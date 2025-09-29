# ros2 node for controlling a robotic arm to handle noodles
# This code is designed to work with the DSR_ROBOT2 library for robotic control

import rclpy
import DR_init
import threading
import time
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from order_interface.msg import Order
from order_interface.srv import OrderService
import sys
from rclpy.callback_groups import ReentrantCallbackGroup  # ReentrantCallbackGroup 임포트
from std_msgs.msg import String


MAX_COOKING_SLOTS = 3

ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"
VELOCITY, ACC = 30, 30

DR_init.__dsr__id = ROBOT_ID
DR_init.__dsr__model = ROBOT_MODEL
ON, OFF = 1, 0
SYSTEM_COOKING = 0
SYSTEM_DONE = -1



    ##############################################################################
    ##############################################################################
    ##############################################################################

#### UI와 통신하는 노드
class RobotMadeCom(Node):
    """
    'start_cooking' 토픽을 구독하여 조리를 시작하고,
    완료되면 'order_finish' 토픽을 발행하는 노드
    """
    def __init__(self):
        super().__init__('robot_made_com', namespace=ROBOT_ID)
        # --- 토픽 발행자 및 구독자 생성 ---
        self.publisher_ = self.create_publisher(Order, 'order_finish', 10)
        self.subscription = self.create_subscription(
            Order,
            'start_cooking',
            self.start_cooking_callback,
            10)
        
        

        self.get_logger().info("로봇 조리 시스템 가동 준비 완료.")

    def start_cooking_callback(self, msg):
        """
        조리 시작 신호를 받으면 실행되는 콜백
        """
        self.get_logger().info(f"주문 로그: [주문번호: {msg.order_id}] '{msg.menu}' 조리가 곧 종료됩니다.")
        
        # 별도의 스레드에서 조리 시뮬레이션을 실행하여 콜백이 차단되는 것을 방지
        threading.Thread(target=self.simulate_cooking, args=(msg,)).start()

    def simulate_cooking(self, order_msg):
        """
        1초간의 조리 과정을 시뮬레이션하고 완료 토픽을 발행
        """
        time.sleep(1)
        
        # 조리 완료 토픽 발행
        finish_msg = Order()
        finish_msg.order_id = order_msg.order_id
        finish_msg.menu = order_msg.menu
        self.publisher_.publish(finish_msg)
        self.get_logger().info(f"주문 종료: [주문번호: {finish_msg.order_id}] '{finish_msg.menu}' 조리 완료")

    ##############################################################################
    ##############################################################################
    ##############################################################################


class OrderGucksuServerWithRobot(Node):
    def __init__(self, initial_cooking_count=0):
        super().__init__('order_gucksu_server_with_robot', namespace=ROBOT_ID)
        self.declare_parameter('system_cooking', -1)
        self.declare_parameter('system_done', -1)

        self.callback_group = ReentrantCallbackGroup()
        self.srv = self.create_service(OrderService, 'order_service', self.order_service_callback, callback_group=self.callback_group)

        self.start_cooking_publisher = self.create_publisher(Order, 'start_cooking', 10)
        self.subscription = self.create_subscription(Order, 'order_finish', self.topic_callback, 10, callback_group=self.callback_group)

        self.cooking_in_progress = initial_cooking_count
        self.pending_orders = {}
        self.pending_orders_lock = threading.Lock()
        self.condition = threading.Condition()

        self.get_logger().info("--- 잔치국수 전문점 (로봇 협업) 개점 ---")

    def cooking_status_callback(self, msg):
        """
        noodle_gemini.py로부터 조리 완료 메시지를 수신하는 콜백 함수
        """
        self.get_logger().info(f'Received cooking status: "{msg.data}"')
        parts = msg.data.split(':')
        if len(parts) == 2 and parts[0] == 'cooking_done':
            system_done_value = int(parts[1])
            self.get_logger().info(f'Cooking step {system_done_value} is complete.')
            # 여기에 다음 로직을 추가합니다.
            # 예를 들어, start_cooking 토픽을 구독하거나 다른 작업을 시작할 수 있습니다.
            

    def order_service_callback(self, request, response):
        self.get_logger().info(f"새 주문 접수: {request.order_num}")
        event = threading.Event()
        with self.pending_orders_lock:
            self.pending_orders[request.order_num] = {'response': response, 'event': event}

        start_msg = Order()
        start_msg.order_id = request.order_num
        start_msg.menu = request.menu
        self.start_cooking_publisher.publish(start_msg)

        event.wait()
        self.get_logger().info(f"조리 완료: {request.order_num}")
        return response

    def topic_callback(self, msg):
        with self.pending_orders_lock:
            if msg.order_id in self.pending_orders:
                order_info = self.pending_orders.pop(msg.order_id)
                response = order_info['response']
                event = order_info['event']

                response.order_num = msg.order_id
                response.menu = msg.menu
                response.status = "조리 완료"
                event.set()






def main(args=None):
    rclpy.init(args=args)

    ##############################################################################
    ##############################################################################
    ##############################################################################
    # 로봇 제어와 로깅을 위한 메인 노드 생성
    node = rclpy.create_node("noodle_ros_node", namespace=ROBOT_ID)
    node.declare_parameter('system_cooking', -1)
    node.declare_parameter('system_done', -1)
    DR_init.__dsr__node = node




     ### 국수 UI 서버와 합치는 중...
    initial_cooking_count = 0
    if len(sys.argv) > 1:
        try:
            initial_cooking_count = int(sys.argv[1])
        except ValueError:
            print("오류: 초기 조리 개수는 정수여야 합니다.")
            sys.exit(1)


    server_node = OrderGucksuServerWithRobot(initial_cooking_count)
    executor1 = MultiThreadedExecutor()
    executor1.add_node(server_node)
    executor_thread1 = threading.Thread(target=executor1.spin, daemon=True)
    executor_thread1.start()





    # 토픽 발행을 위한 노드 인스턴스 생성
    minimal_publisher = RobotMadeCom()

    # --- 멀티스레드 Executor 설정 ---
    # 여러 노드의 콜백을 동시에 처리할 수 있는 Executor 생성
    executor2 = MultiThreadedExecutor()
    executor2.add_node(minimal_publisher)

    # Executor를 별도의 백그라운드 스레드에서 실행
    # 이렇게 하면 spin()이 메인 스레드를 막지 않습니다.
    # executor_thread = threading.Thread(target=executor.spin, daemon=True)
    # executor_thread.start()

    node.get_logger().info("Publisher has started in \
        a background thread.")


    ##############################################################################
    ##############################################################################
    ##############################################################################


    try:
        from DSR_ROBOT2 import (
            set_digital_output,
            get_digital_input,
            set_tool,
            set_tcp,
            movej,
            movel,
            movec,
            movesx,
            moveb,
            amovel,
            move_periodic,
            release_compliance_ctrl,
            release_force,
            check_force_condition,
            check_position_condition,
            task_compliance_ctrl,
            set_desired_force,
            get_current_posx,
            set_singular_handling,
            set_velj,
            set_accj,
            set_velx,
            set_accx,
            wait,
            DR_BASE,
            DR_AVOID,
            DR_AXIS_Z,
            DR_FC_MOD_REL,
            DR_MV_MOD_REL,
            # DR_OFF,
            DR_TOOL,
            DR_LINE,
            DR_CIRCLE,
        )

        from DR_common2 import posj, posx, posb
    except ImportError as e:
        print(f"Error importing DSR_ROBOT2 : {e}")
        return

    set_tool("Tool Weight_2FG")
    set_tcp("2FG_TCP")


    def grip():
        print("set for digital output 1 0 for grip")
        set_digital_output(2, OFF)
        set_digital_output(3, OFF)
        set_digital_output(4, OFF)
        set_digital_output(1, ON)
        wait(0.5)

    def release_40():
        set_digital_output(1, OFF)
        set_digital_output(3, OFF)
        set_digital_output(4, OFF)
        set_digital_output(2, ON)
        wait(0.5)

    def release_60():
        set_digital_output(1, OFF)
        set_digital_output(2, OFF)
        set_digital_output(4, OFF)
        set_digital_output(3, ON)
        wait(0.5)

    def release_80():
        set_digital_output(1, OFF)
        set_digital_output(2, OFF)
        set_digital_output(3, OFF)
        set_digital_output(4, ON)
        wait(0.5)

    def trans(pos: list[float], delta: list[float], ref: int = DR_BASE, ref_out: int = DR_BASE) -> list[float]:

        if len(pos) != 6 or len(delta) != 6:
            raise ValueError("pos와 delta는 각각 6개의 float 값을 포함하는 리스트여야 합니다.")

        # 결과를 저장할 새로운 리스트 생성
        result_pos = []

        # 각 인덱스에 맞춰 값 더하기
        for i in range(6):
            result_pos.append(pos[i] + delta[i])

        return result_pos

    def force_ctrl():
        print("Starting task_compliance_ctrl")
        task_compliance_ctrl(stx=[1500, 1500, 1500, 200, 200, 200]) #힘 제어 시작
        time.sleep(0.5)
        fd = [0, 0, -50, 0, 0, 0]
        fctrl_dir= [0, 0, 1, 0, 0, 0]
        print("Starting set_desired_force")
        set_desired_force(fd=fd, dir=fctrl_dir, mod=DR_FC_MOD_REL) 

        # 외력이 0 이상 5 이하이면 0
        # 외력이 5 초과이면 -1
        while not check_force_condition(DR_AXIS_Z, max=5):
            print("Waiting for an external force greater than 5 ")
            time.sleep(0.5)
            pass

        print("Starting release_force")
        release_force()
        time.sleep(0.5)

        print("Starting release_compliance_ctrl")      
        release_compliance_ctrl()

        return True

    def pick_cup():
        print("pick cup")
        movel([0, 0, 18, 0, 0, 0], mod=DR_MV_MOD_REL) #살짝 올림        # amovel?
        release_80()
        movel([0, 0, -27, 0, 0, 0], mod=DR_MV_MOD_REL) #잡으러 내림
        release_60()
        movel([0, 0, +120, 0, 0, 0], mod=DR_MV_MOD_REL) #올려!!!!!!!!


    def put_cup(cup_setting_pos: list[float], delta_z: list[float]):
        pos1 = posb(DR_LINE, trans(cup_setting_pos, delta_z), radius=20)  # 컵 세팅 위치 위로 이동
        pos2 = posb(DR_LINE, trans(cup_setting_pos, [0, 0, 18, 0, 0, 0]), radius=10)  # 컵 세팅 위치로 이동
        b_list = [pos1, pos2]

        print("moveb start")
        moveb(b_list)
        print("moveb end")

        if force_ctrl():
            release_80()  # 컵 놓기
        movel(trans(cup_setting_pos, delta_z)) # 컵 세팅 위치 위로 이동

    # 손잡이 근처로 이동해서 채를 집는 함수
    def pick_up_strainer(pos: list[float], delta_z: list[float]):

        release_40()
        print('release_40')
        # moveb로 블렌딩
        pos1 = posb(DR_LINE, trans(pos, delta_z), radius=20)
        pos2 = posb(DR_LINE, pos)
        b_list = [pos1, pos2]
        moveb(b_list)

        grip()
        movel(trans(pos, delta_z))       #채 들어올림
        
        
    # 면 삶아지면 컵으로 이동해서 면 떨구고 돌아오기.
    def after_pick_strainer(picking_pos: list[float], waiting_pos: list[float], putting_pos: list[float], delta_z: list[float]):

        # moveb로 블렌딩
        seg_waiting = posb(DR_LINE, waiting_pos, radius=20)
        seg_putting = posb(DR_LINE, putting_pos)

        seg_picking_up = posb(DR_LINE, trans(picking_pos, delta_z), radius=20)
        seg_picking = posb(DR_LINE, picking_pos)
        b_list = [seg_waiting, seg_putting]
        moveb(b_list)
        wait(0.2)
        noodle_putting()

        b_list2 = [seg_waiting, seg_picking_up, seg_picking]

        moveb(b_list2)
        
        release_40()
        movel(trans(picking_pos, delta_z))
    
    def pick_and_put_noodle(n: list[float], strainer_n: list[float], delta_z: list[float]): # 면 집어 들고 채에 투하
        print("pick and put noodle start")
        release_60()
        wait(0.1)

        pos1 = posb(DR_LINE, trans(n, delta_z), radius=20)  #면 위로 이동
        pos2 = posb(DR_LINE, n)                  #면 집기

        b_list = [pos1, pos2]
        print("moveb start")
        moveb(b_list)
        print("moveb end")

        grip()
        start_time = time.time() # 시작 시간 기록
        
        # moveb로 블렌딩
        pos_n_trans = trans(trans(n, delta_z),delta_z)
        seg_n = posb(DR_LINE, pos_n_trans, radius=100)
        seg_c = posb(DR_CIRCLE, trans(n, delta_xyz), trans(strainer_n, delta_z), radius=49)
        seg_strainer = posb(DR_LINE, strainer_n)
        b_list = [seg_n, seg_c, seg_strainer]
        print("moveb start")
        moveb(b_list)
        print("moveb end")
        
        end_time = time.time() # 종료 시간 기록

        execution_time = end_time - start_time
        print(f"{execution_time:.6f}")

        release_60()
        amovel([0, 0, 50, 0, 0, 0], mod=DR_MV_MOD_REL) #올려!!!!!!!!


    def watering(): # 물 털기
        movej([0, 0, 0, 0, +15, 0], mod = DR_MV_MOD_REL)
        amp = [0, 0, 15, 0, 0, 0]
        period = [0.6, 0, 0.6, 0, 0, 0]
        repeat = 6
        atime = 0.2
        ref = DR_TOOL
        move_periodic(amp, period, atime, repeat, ref)
    def noodle_putting(): # 면 털기
        amp = [0, 10, -10, 0, 0, 0]
        period = [0, 0.6, 0.6, 0, 0, 0]
        repeat = 3
        atime = 0.1
        ref = DR_BASE
        move_periodic(amp, period, atime, repeat, ref)

    def cooking_step1(n, strainer_n, cup_setting_pos_n, delta_z):
        pick_and_put_noodle(n, strainer_n, delta_z)  # 면 집기 및 투하
        movec(pos1=trans(n, delta_xyz), pos2=cup)      # 채 위로 이동 movec 이용해서 이동해보려고
        release_60()
        if force_ctrl():  # 힘 제어 시작
            pick_cup()
            put_cup(cup_setting_pos_n, delta_z)  # 컵 세팅 위치로 이동

    def cooking_step2(n_pick, n_put, delta_z):
        pick_up_strainer(n_pick, delta_z)  # 채 집기
        watering()  # 물 털기
        after_pick_strainer(n_pick, waiting_pos, n_put, delta_z) # 면 컵에 담기

    home = posj(-90, 0, 90, 180, -90, 0) # 홈 위치
    n1_pick = posx(384.52, 16.85, 157.88, 39.24, 133.29, -89.14) # 1번 채 손잡이
    n2_pick = posx(387.12, -69.28, 166.51, 42.67, 131.82, -87.29) # 2번 채 손잡이

    waiting_pos = posx(606.76, -83.66, 291.49, 160.58, -155.47, -14.72) # 국수 투하 전 대기 위치

    cup_setting_pos1 = posx(598.58, 38.68, 85.0, 176.12, -180.0, 86.43) #  컵 대기 위치1
    cup_setting_pos2 = posx(598.58, -138.54, 85.0, 171.91, -180.0, 82.22) #  컵 대기 위치2  

    n1_put = posx(597.31, 78.07, 183.78, 100.97, -114.33, -81.09) # 1번 국수 컵에 투하
    n2_put = posx(597.31, -110.02, 183.81, 96.52, -117.59, -80.12) # 2번 국수 컵에 투하
    delta_z = [0, 0, 100, 0, 0, 0] # 축이동 trans변수
    delta_xyz = [200, 150, 200, 0, 0, 0] # 이동 trans변수
    n = posx(268.53, -227.29, 1.61, 109.73, -180.0, -70.57)    # 면 위치 좌표
    strainer_1 = posx(420.53, 40.99, 116.96, 172.48, 178.92, 81.92)   # 면 채1에 투하 좌표
    strainer_2 = posx(419.11, -44.16, 115.83, 168.34, 178.77, 77.92)   # 면 채2에 투하 좌표

    cup = posx(384.53, -215.98, 150.53, 148.58, 179.85, 56.52)     # 컵 위치

    set_singular_handling(DR_AVOID)
    set_velj(30.0)
    set_accj(30.0)
    set_velx(100.0, 40.625)
    set_accx(500.0, 161.5)

    global SYSTEM_COOKING, SYSTEM_DONE
    while rclpy.ok():
        
        # SYSTEM_DONE = node.get_parameter('system_done').get_parameter_value().integer_value
        SYSTEM_COOKING = node.get_parameter('system_cooking').get_parameter_value().integer_value
        
        
        print(f"Current SYSTEM_COOKING Value: {SYSTEM_COOKING}\n")
        print(f"Moving to joint position: {home}\n")
        movej(home, vel=40, acc=20)  # 홈 위치로 이동
        
        if SYSTEM_COOKING != -1:
            if SYSTEM_COOKING / 2 == 0:
                SYSTEM_COOKING = 0
            else:
                SYSTEM_COOKING = 1

        # 상태 변수 추가해서 조리중인 경우에 맞게 좌표이동
        if SYSTEM_COOKING == 0:
           cooking_step1(n, strainer_1, cup_setting_pos1, delta_z)  # 면 집기 및 투하
           SYSTEM_DONE = 0
        elif SYSTEM_COOKING == 1:
           cooking_step1(n, strainer_2, cup_setting_pos2, delta_z)  # 면 집기 및 투하
           SYSTEM_DONE = 1 
        else:
            print("Invalid cooking system state. Please check the configuration.\n")
            print("SYSTEM_COOKING is invalid or idle (-1). Waiting for command...")
            time.sleep(1)
            # break
            continue

        # 상태 변수 추가해서 조리 완료인 경우에 맞게 시쿼스 진행
        if SYSTEM_DONE == 0 or SYSTEM_DONE == 1:
            if SYSTEM_DONE == 0:
                cooking_step2(n1_pick, n1_put, delta_z)  # 면 집기 및 투하

                print("조리 완료! 토픽 발행 start!\n")
                executor_thread2 = threading.Thread(target=executor2.spin_once, daemon=True)
                executor_thread2.start()
                print("조리 완료! 토픽 발행! stop\n")
                SYSTEM_DONE = -1

            elif SYSTEM_DONE == 1:
                cooking_step2(n2_pick, n2_put, delta_z)  # 면 집기 및 투하

                print("조리 완료! 토픽 발행 start!\n")
                executor_thread2 = threading.Thread(target=executor2.spin_once, daemon=True)
                executor_thread2.start()
                print("조리 완료! 토픽 발행! stop\n")
                SYSTEM_DONE = -1
        else:
            print("Invalid cooking system state. Please check the configuration.")
            pass

        node.set_parameters([rclpy.parameter.Parameter('system_cooking', rclpy.Parameter.Type.INTEGER, -1)])
        SYSTEM_DONE = -1

        wait(1.0)


    node.get_logger().info("Shutting down...")
    
    rclpy.shutdown()
    server_node.destroy_node()
    # 백그라운드 스레드가 완전히 종료될 때까지 대기
    executor_thread1.join()
    executor_thread2.join()
    node.get_logger().info("Shutdown complete.")


if __name__ == "__main__":
    main()