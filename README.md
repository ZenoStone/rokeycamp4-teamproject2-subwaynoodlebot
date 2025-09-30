# rokeycamp4-teamproject2-subwaynoodlebot
로키 부트캠프 4기 협동1 프로젝트 결과물 입니다

두산의 M0609 로봇팔을 활용하여 지하철 한 켠이라는 작은 공간에서 무인으로 국수를 조리하고 제공하는 국수 로봇 프로젝트입니다


# 실행방법
1. subwaynoodlebot_setup.sh 를 다운 받은 다음 실행하면 필요한 설치 파일 및 파일구조가 형성됩니다
> cd ~/Downloads
> chmod +x subwaynoodlebot_setup.sh
> ./subwaynoodlebot_setup.sh
> Setup Finished! # 문구 출력시 정상적으로 다운로드가 완료된 상태임

2. 다운로드 후 터미널 실행해서 아래의 명령어 순차 입력
> cd ~/ros2_ws 
> colcon build --symlink-install


# RECORD
> 250929 레포지토리에 코드 업로드 완료
- 기본적인 설치는 subwaynoodlebot_setup.sh 를 실행함으로서 구현, but 테스트 필요

> 250930 README에 실행방법 작성 및 setup.sh 파일 수정 완


## License
This project is licensed under the MIT License. See the LICENSE file for details.