#!/bin/bash
# portfolio_setup.sh - ROS2 Doosan Robot Project Portfolio Setup Script
# This script automates the setup of the entire project, including custom code.

 #  1. 필요한 시스템 및 ROS 패키지를 설치합니다.
 #  2. 원본 두산 로보틱스 GitHub 저장소(DoosanBootcam3rdCo1)를 복제합니다.
 #  3. 사용자의 포트폴리오 GitHub 저장소를 복제합니다. (이 부분은 사용자가 직접 만들고 URL을 수정해야 합니다)
 #  4. 복제된 사용자의 파일들을 DoosanBootcam3rdCo1 내의 올바른 위치로 이동시킵니다.
 #  5. 프로젝트 빌드 및 환경 설정을 마무리합니다.


set -e # Exit immediately if a command exits with a non-zero status.

# --- Color Definitions for better readability ---
PURPLE='\033[0;35m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# --- Helper Functions ---
print_header() {
    echo -e "\n${PURPLE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${PURPLE}🚀 $1${NC}"
    echo -e "${PURPLE}════════════════════════════════════════════════════════════════${NC}\n"
}

print_step() {
    echo -e "${BLUE}🔹 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# =============================================================================
# Phase 1: Install System and ROS Dependencies
# =============================================================================
print_header "Installing System and ROS Dependencies"

print_step "Updating package lists..."
sudo apt-get update

print_step "Installing essential ROS2 and Gazebo packages..."
sudo apt-get install -y \
  ros-humble-gazebo-* \
  ros-humble-cartographer \
  ros-humble-cartographer-ros \
  ros-humble-navigation2 \
  ros-humble-nav2-bringup \
  ros-humble-dynamixel-sdk \
  ros-humble-moveit \
  ros-humble-ros2-control \
  ros-humble-ros2-controllers \
  ros-humble-xacro \
  python3-vcstool \
  python3-colcon-common-extensions \
  git

print_success "System and ROS dependencies installed."

# =============================================================================
# Phase 2: Clone Required Repositories
# =============================================================================
print_header "Cloning Repositories"

# --- Clone the base Doosan Robotics repository ---
print_step "Cloning DoosanBootcam3rdCo1 repository (branch: humble-v0.1.1)..."
git clone -b humble-v0.1.1 https://github.com/doosan-robotics/DoosanBootcam3rdCo1.git

# --- Clone the Gazebo-ROS2 control repository ---
print_step "Cloning gz_ros2_control repository..."
git clone https://github.com/gazebosim/gz_ros2_control.git

# --- Clone YOUR portfolio project repository ---
print_step "Cloning your portfolio project repository..."
#
# ❗❗❗ IMPORTANT ❗❗❗
# YOU MUST REPLACE THE URL BELOW WITH YOUR OWN GITHUB REPOSITORY URL.
# Your repository should contain:
#   - kiosk_main.py
#   - noodle_ros_node.py
#   - order_interface/
#   - img_folder/
#   - ui/
#
git clone https://github.com/YOUR_USERNAME/YOUR_PORTFOLIO_REPO.git my_custom_project ### 깃허브 링크 수정 필요함

print_success "All repositories cloned."

# =============================================================================
# Phase 3: Arrange Custom Project Files
# =============================================================================
print_header "Arranging Custom Project Files"

# --- Move your custom files to the correct locations ---
print_step "Moving custom files into the Doosan project structure..."

# Move the order_interface package to the src root
mv my_custom_project/order_interface .
print_success "Moved 'order_interface' to src/."

# Ensure the target directories exist before moving files
mkdir -p DoosanBootcam3rdCo1/dsr_rokey/rokey/rokey/basic
mkdir -p DoosanBootcam3rdCo1/dsr_rokey/rokey/

# Move Python scripts
mv my_custom_project/kiosk_main.py DoosanBootcam3rdCo1/dsr_rokey/rokey/rokey/basic/
mv my_custom_project/noodle_ros_node.py DoosanBootcam3rdCo1/dsr_rokey/rokey/rokey/basic/
print_success "Moved Python scripts to dsr_rokey/rokey/rokey/basic/."

# Move asset folders
mv my_custom_project/img_folder DoosanBootcam3rdCo1/dsr_rokey/rokey/
mv my_custom_project/ui DoosanBootcam3rdCo1/dsr_rokey/rokey/
print_success "Moved 'img_folder' and 'ui' folders to dsr_rokey/rokey/."

# --- Clean up the cloned custom project directory ---
print_step "Cleaning up temporary project folder..."
rm -rf my_custom_project
print_success "Cleanup complete."

# =============================================================================
# Phase 4: Final Setup and Build
# =============================================================================
print_header "Finalizing Setup"

print_step "Importing additional repositories using vcs..."
vcs import < gz_ros2_control/gz_ros2_control.humble.repos

print_step "Adding colcon_cd to .bashrc for convenience..."
echo "source /usr/share/colcon_cd/function/colcon_cd.sh" >> ~/.bashrc
echo "export _colcon_cd_root=$(pwd | sed 's|/src$||')" >> ~/.bashrc

print_success "Environment setup is complete."
echo -e "${YELLOW}You may need to run 'source ~/.bashrc' or open a new terminal for changes to take effect.${NC}"

# =============================================================================
# Completion Message
# =============================================================================
print_header "Setup Finished!"
echo -e "${GREEN}Your project environment is ready.${NC}"
echo -e "The next steps are:"
echo -e "1. Open a ${BLUE}new terminal${NC}."
echo -e "2. Navigate to your workspace root: ${BLUE}cd $(pwd | sed 's|/src$||')${NC}"
echo -e "3. Build the workspace: ${BLUE}colcon build --symlink-install${NC}"
echo -e ""
echo -e "${RED}Remember to replace the placeholder URL in this script if you haven't already!${NC}"
echo -e ""
