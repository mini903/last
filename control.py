import lgpio
import time
import math

# --- 핀 구성 (BCM) ---
PWM_LEFT = 17
DIR_LEFT = 27
PWM_RIGHT = 18
DIR_RIGHT = 22
PWM_LIFT = 23
DIR_LIFT = 24

# --- 전역 변수 ---
pi = -1  # lgpio 칩 핸들
MAX_SPEED = 2000 # PWM 펄스 폭 (모터에 맞게 조정 가능)
FREQ = 1000      # PWM 주파수 (Hz)
log_sender = None

# --- 로깅 함수 ---
def set_logger(sender):
    global log_sender
    log_sender = sender

def send_log(msg):
    if log_sender:
        log_sender(msg)
    else:
        print(f"[LOG] {msg}")

# --- GPIO 초기화 ---
def init_gpio():
    global pi
    try:
        pi = lgpio.gpiochip_open(0)
       
        pins_to_claim = {PWM_LEFT, DIR_LEFT, PWM_RIGHT, DIR_RIGHT, PWM_LIFT, DIR_LIFT}
        for pin in pins_to_claim:
            lgpio.gpio_claim_output(pi, pin, 0)
       
        # 주행 모터 PWM 시작 (리프트는 단순 ON/OFF로 가정)
        lgpio.tx_pwm(pi, PWM_LEFT, FREQ, 0)
        lgpio.tx_pwm(pi, PWM_RIGHT, FREQ, 0)
           
        send_log("✅ GPIO 초기화 및 PWM 설정 완료")
       
    except lgpio.error as e:
        send_log(f"❌ GPIO 초기화 오류: {e}")
        pi = -1
       
init_gpio()

# --- 모터 제어 함수 ---
def set_motor_speed(pwm_pin, dir_pin, speed):
    if pi < 0: return

    speed_abs = abs(speed)
    # PWM 듀티 사이클 계산
    duty_cycle = int((speed_abs / MAX_SPEED) * 1000000)
    duty_cycle = max(0, min(1000000, duty_cycle))

    # 방향 설정 (L298N 가정 시)
    direction = 1 if speed >= 0 else 0
    lgpio.gpio_write(pi, dir_pin, direction)
   
    # PWM 속도 설정
    lgpio.tx_pwm(pi, pwm_pin, FREQ, duty_cycle)

def stop_drive():
    """주행 모터 정지"""
    if pi < 0: return
    lgpio.tx_pwm(pi, PWM_LEFT, FREQ, 0)
    lgpio.tx_pwm(pi, PWM_RIGHT, FREQ, 0)

def drive(x, y):
    """조이스틱 입력 (x: 회전/리프트, y: 전진/후진)"""
    if pi < 0: return

    # 데드존 (정지 상태 유지)
    if abs(x) < 0.05 and abs(y) < 0.05:
        stop()
        return

    # 1. 리프트 제어 (X축 강한 입력)
    if abs(x) > 0.8:
        lift_speed = x * MAX_SPEED
       
        if lift_speed > 0: # 리프트 UP
            lgpio.gpio_write(pi, DIR_LIFT, 1)
            lgpio.gpio_write(pi, PWM_LIFT, 1)
        else: # 리프트 DOWN
            lgpio.gpio_write(pi, DIR_LIFT, 0)
            lgpio.gpio_write(pi, PWM_LIFT, 1)
       
        stop_drive() # 주행 모터 정지
        return
    else:
        lgpio.gpio_write(pi, PWM_LIFT, 0) # 리프트 정지

    # 2. 주행 제어
    turn = x * 0.7 # 회전량
    power = -y     # 전진/후진 (Y축 반전)

    left_speed = power + turn
    right_speed = power - turn

    # 속도 클리핑 및 최종 속도 계산
    left_speed = max(-1.0, min(1.0, left_speed)) * MAX_SPEED
    right_speed = max(-1.0, min(1.0, right_speed)) * MAX_SPEED

    set_motor_speed(PWM_LEFT, DIR_LEFT, left_speed)
    set_motor_speed(PWM_RIGHT, DIR_RIGHT, right_speed)

    send_log(f"🚗 drive L:{int(left_speed)} R:{int(right_speed)}")


def stop():
    """모든 모터 정지"""
    global pi
    if pi < 0: return
   
    stop_drive()
    lgpio.gpio_write(pi, PWM_LIFT, 0) # 리프트 정지
    send_log("🛑 모든 모터 정지")
