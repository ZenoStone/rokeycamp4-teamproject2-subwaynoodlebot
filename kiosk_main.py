import sys
import os
from PyQt5 import QtWidgets, uic, QtCore
import rclpy
from rclpy.node import Node
from order_interface.srv import OrderService
from rcl_interfaces.srv import SetParameters
from rclpy.parameter import Parameter
from collections import deque


### 
from ament_index_python.packages import get_package_share_directory

#### dusan setting
import DR_init

MAX_COOKING_SLOTS = 3
ROBOT_ID = "dsr01"
DR_init.__dsr__id = ROBOT_ID

"""

기존의 os.path.dirname(__file__) 방식은 install 디렉토리 구조에서는
더 이상 유효하지 않습니다.
ROS 2가 제공하는 ament_index_python을 사용하여
share 디렉토리에 설치된 파일의 경로를 찾아야 합니다.

"""

MAX_CONCURRENT_ORDERS = 99 # 3
MAX_QUEUE_DISPLAY = 10

class KioskNode(Node):
    def __init__(self):
        super().__init__('kiosk_node', namespace=ROBOT_ID)
        self.next_order_number = 1
        self.cooking_queue = deque()
        self.waiting_queue = deque()
        self.completed_orders = deque(maxlen=MAX_QUEUE_DISPLAY)

        self.cli = self.create_client(OrderService, 'order_service')
        self.param_cli = self.create_client(SetParameters, '/dsr01/noodle_ros_node/set_parameters')
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('order_service 준비 중...')
        while not self.param_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Parameter service not available, waiting...')

    def update_robot_status(self):
        req = SetParameters.Request()
        param = Parameter(name='system_cooking', value=len(self.cooking_queue) - 1)
        req.parameters.append(param.to_parameter_msg())
        self.param_cli.call_async(req)

    def send_order(self, order_num, menu, status, callback):
        request = OrderService.Request()
        request.order_num = order_num
        request.menu = menu
        request.status = status

        future = self.cli.call_async(request)

        def response_callback(fut):
            try:
                result = fut.result()
                if result.order_num in self.cooking_queue:
                    self.cooking_queue.remove(result.order_num)
                    self.completed_orders.append(result.order_num)

                if self.waiting_queue:
                    next_order = self.waiting_queue.popleft()
                    self.cooking_queue.append(next_order)
                    self.send_order(next_order, "잔치국수", "조리중", callback)

                self.update_robot_status()
                callback()
            except Exception as e:
                self.get_logger().error(f"서비스 실패: {e}")
                QtWidgets.QMessageBox.critical(None, "에러", "서비스 실패. 다시 시도해주세요.")

        future.add_done_callback(response_callback)

class KioskApp:
    def __init__(self, node):
        self.node = node
        self.order_ui = None  # order_ui를 클래스 속성으로 초기화
        self.load_open_ui()


    def load_open_ui(self): #### UI 불러오는 부분
        # open_ui_path = os.path.join(os.path.dirname(__file__), 'open_diy.ui')


        # 수정된 경로 코드 -> gemini를 통해서 ros2 구조에 맞는 방식으로 경로 부분을 수정함
        # 'rokey' 패키지의 share 디렉토리 경로를 가져옴
        share_dir = get_package_share_directory('rokey')
        # share 디렉토리 아래 ui 폴더에 있는 kiosk_ui.ui 파일의 전체 경로를 생성 
        order_ui_path = os.path.join(share_dir, 'ui', 'open_diy.ui')

        self.open_ui = uic.loadUi(order_ui_path) ### open_ui_path로 되어 있었음 -> gemini를 통해서 ros2 구조에 맞는 방식으로 경로 부분을 수정함


        self.open_ui.change_window.clicked.connect(self.load_order_ui)
        self.update_all() # 초기화면에서도 업데이트
        self.open_ui.show()

    def go_to_home(self):
        if self.order_ui:
            self.order_ui.close()
        self.load_open_ui()

    def update_total_price(self):
        try:
            # 가격을 UI 레이블에서 직접 읽는 대신 상수로 정의하여 사용합니다.
            # label_7 (비빔국수) 가격: 1500
            # label_8 (잔치국수) 가격: 1300
            price1 = 1500 
            quantity1 = self.order_ui.orderQuantitySpin_5.value()

            price2 = 1300
            quantity2 = self.order_ui.orderQuantitySpin_4.value()

            total_price = (price1 * quantity1) + (price2 * quantity2)

            self.order_ui.label_10.setText(f"총 결제 금액 : {total_price}원")
        except AttributeError as e:
            # order_ui가 아직 완전히 로드되지 않았을 때 발생할 수 있는 오류를 처리합니다.
            if self.order_ui and self.order_ui.label_10:
                 self.order_ui.label_10.setText("총 결제 금액 : - 원")
            self.node.get_logger().warn(f"Could not update total price: {e}")


    def load_order_ui(self):
        if self.open_ui:
            self.open_ui.close()
        # order_ui_path = os.path.join(os.path.dirname(__file__), 'kiosk_diy.ui') #### UI 불러오는 부분 
        
        # 수정된 경로 코드 -> gemini를 통해서 ros2 구조에 맞는 방식으로 경로 부분을 수정함
        # 'rokey' 패키지의 share 디렉토리 경로를 가져옴
        share_dir = get_package_share_directory('rokey') # 이전에는 order_system
        # share 디렉토리 아래 ui 폴더에 있는 kiosk_ui.ui 파일의 전체 경로를 생성 
        order_ui_path = os.path.join(share_dir, 'ui', 'kiosk_diy.ui')
        
        
        self.order_ui = uic.loadUi(order_ui_path)

        self.order_ui.orderButton.clicked.connect(self.handle_order)
        self.order_ui.HomeButton.clicked.connect(self.go_to_home)

        # --- SpinBox 설정 ---
        # 비빔국수 수량 (orderQuantitySpin_5)
        self.order_ui.orderQuantitySpin_5.setMinimum(0)
        self.order_ui.orderQuantitySpin_5.setMaximum(99)
        self.order_ui.orderQuantitySpin_5.setValue(0)

        # 잔치국수 수량 (orderQuantitySpin_4)
        self.order_ui.orderQuantitySpin_4.setMinimum(0)
        self.order_ui.orderQuantitySpin_4.setMaximum(99)
        self.order_ui.orderQuantitySpin_4.setValue(0)

        # --- 시그널 연결 ---
        self.order_ui.orderQuantitySpin_5.valueChanged.connect(self.update_total_price)
        self.order_ui.orderQuantitySpin_4.valueChanged.connect(self.update_total_price)

        self.update_all() # 주문 화면으로 전환 시에도 업데이트
        self.update_total_price() # 초기 총액 계산
        self.order_ui.show()

    def handle_order(self):
        order_num = self.node.next_order_number
        self.node.next_order_number += 1
        menu = "잔치국수"

        if len(self.node.cooking_queue) < MAX_CONCURRENT_ORDERS:
            self.node.cooking_queue.append(order_num)
            self.node.send_order(order_num, menu, "조리중", self.update_all)
            self.node.update_robot_status()
        else:
            self.node.waiting_queue.append(order_num)

        self.update_all()

    def update_all(self):
        self.update_ui(self.open_ui, "waitingQueue_2", "doneQueue_2")
        if self.order_ui: # order_ui가 로드되었을 때만 업데이트
            self.update_ui(self.order_ui, "waitingQueue_2", "doneQueue_2")


    def update_ui(self, ui, waiting_widget_name, done_widget_name):
        if not ui or not ui.isVisible():
            return
            
        waiting_widget = getattr(ui, waiting_widget_name, None)
        done_widget = getattr(ui, done_widget_name, None)

        # '조리중'과 '대기중' 목록을 합쳐서 최신 10개만 표시 -> 계속 하단에 생성됨. 최대치 삭제함
        cooking_list = [f"#{o} - 조리중\n" for o in self.node.cooking_queue]
        waiting_list = [f"#{o} - 대기중\n" for o in self.node.waiting_queue]
        full_waiting_list = cooking_list + waiting_list
        
        # 제한 없이 모든 대기/조리중인 주문을 표시
        display_waiting_list = full_waiting_list
        waiting_text = "".join(display_waiting_list)

        # '완료' 목록은 deque의 maxlen에 의해 자동으로 10개 유지됨
        done_text = "".join([f"#{o} - 완료\n" for o in self.node.completed_orders])

        if waiting_widget:
            waiting_widget.setPlainText(waiting_text)
        if done_widget:
            done_widget.setPlainText(done_text)


def main(args=None):
    rclpy.init(args=args)
    app = QtWidgets.QApplication(sys.argv)

    node = KioskNode()
    gui = KioskApp(node)

    timer = QtCore.QTimer()
    timer.timeout.connect(lambda: rclpy.spin_once(node, timeout_sec=0.01))
    timer.start(10)

    exit_code = app.exec_()
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()