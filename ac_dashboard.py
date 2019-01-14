import ac

try:
    import os
    import sys
    import platform
    sys.path.insert(0, "apps/python/ac_dashboard/DLLs")
    SYSDIR = "stdlib64" if platform.architecture()[0] == "64bit" else "stdlib"
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), SYSDIR))
    os.environ['PATH'] += ';.'

    from info_app import info_app
    from sim_info import info
    from car import Car
    from driver import Driver
    from tyres import (FL, FR, RL, RR, WINDOW_FL, WINDOW_FR, WINDOW_RL,
                       WINDOW_RR)
    from settings import get_user_assists
    from dashboard import (MAIN_APP_TELEMETRY, SPEEDOMETER, FUEL_BAR,
                           FUEL_BUTTON, GEAR_LABEL, SPEED_RPM_BUTTON,
                           TIMES_BUTTON, POS_LAPS_BUTTON, SECTOR_BUTTON)
except Exception as err:
    ac.log("ac_dashboard: " + str(err))
import acsys


APP_WINDOW = None
STATIC_SHARED_MEMORY_IS_READ = False
NUM_CARS = 1  # at least user's CAR
DRIVER = Driver(MAIN_APP_TELEMETRY)
CAR = Car(MAIN_APP_TELEMETRY)


def acMain(ac_version):
    """Main function that is invoked by Assetto Corsa."""
    global APP_WINDOW
    APP_WINDOW = ac.newApp("")
    ac.setSize(APP_WINDOW, 600, 170)
    ac.drawBorder(APP_WINDOW, 0)
    for dashboard_element in (FUEL_BAR, FUEL_BUTTON, GEAR_LABEL,
                              SPEED_RPM_BUTTON, TIMES_BUTTON, POS_LAPS_BUTTON,
                              SECTOR_BUTTON):
        dashboard_element.window = APP_WINDOW

    DRIVER.assists.update(**get_user_assists())
    CAR.name = ac.getCarName(0)
    if CAR.name == 'tatuusfa1':
        SPEEDOMETER.f1_style = True
    ac.addRenderCallback(APP_WINDOW, render_app)

    info_app()

    background = ac.addLabel(APP_WINDOW, "")
    ac.setPosition(background, 0, 0)
    ac.setSize(background, 600, 170)
    app_dir = os.path.dirname(os.path.realpath(__file__))
    ac.setBackgroundTexture(background, app_dir + "/Images/Dashboard.png")
    return "AC Dashboard"


def acUpdate(delta_t):
    """Read data in real time from Assetto Corsa."""
    CAR.in_pits = ac.isCarInPitlane(0)
    DRIVER.position = ac.getCarRealTimeLeaderboardPosition(0)
    completed_laps = ac.getCarState(0, acsys.CS.LapCount)
    if completed_laps > DRIVER.total_laps:
        CAR.fuel_at_start = CAR.fuel  # keep track of fuel on lap change
        DRIVER.last_splits = ac.getLastSplits(0)
        for window, tyre in zip((WINDOW_FL, WINDOW_FR, WINDOW_RL, WINDOW_RR),
                                (FL, FR, RL, RR)):
            ac.setText(window.opt_label,
                       "Opt: {}%".format(round(tyre.time_on_opt * 100 /
                                               sum(DRIVER.last_splits))))
            tyre.time_on_opt = 0
            tyre.time_on_cold = 0
            tyre.time_on_hot = 0

    DRIVER.total_laps = completed_laps
    DRIVER.lap_time = ac.getCarState(0, acsys.CS.LapTime)
    DRIVER.pb = ac.getCarState(0, acsys.CS.BestLap)
    CAR.speed = ac.getCarState(0, acsys.CS.SpeedKMH)
    CAR.rpm = ac.getCarState(0, acsys.CS.RPM)
    FR.temp, FL.temp, RR.temp, RL.temp = ac.getCarState(
        0, acsys.CS.CurrentTyresCoreTemp)
    for window, tyre in zip((WINDOW_FL, WINDOW_FR, WINDOW_RL, WINDOW_RR),
                            (FL, FR, RL, RR)):
        ac.setText(window.starting_label_no,
                   "{}C".format(round(tyre.temp)))

    read_shared_memory()
    CAR.g_forces = ac.getCarState(0, acsys.CS.AccG)
    CAR.gear = ac.getCarState(0, acsys.CS.Gear)
    DRIVER.performance_meter = ac.getCarState(0, acsys.CS.PerformanceMeter)
    MAIN_APP_TELEMETRY.notify(position=dict(car_position=DRIVER.position,
                                   total_cars=NUM_CARS))


def render_app(delta_t):
    # NOTE: call MAIN_APP_TELEMETRY here so it can include any renderings otherwise
    # AC does not render if any renderings are called outside of the function
    # that has been registered with ac.addRenderCallback
    MAIN_APP_TELEMETRY.update()



def read_shared_memory():
    global STATIC_SHARED_MEMORY_IS_READ, NUM_CARS
    if not STATIC_SHARED_MEMORY_IS_READ:
        while CAR.max_fuel is None or CAR.max_rpm is None:
            CAR.max_fuel = info.static.maxFuel
            CAR.max_rpm = info.static.maxRpm
        NUM_CARS = info.static.numCars
        STATIC_SHARED_MEMORY_IS_READ = True

    CAR.tc = info.physics.tc
    CAR.abs = info.physics.abs
    CAR.drs = info.physics.drs
    CAR.fuel = info.physics.fuel

    # Read data once after sector change
    sector_index = info.graphics.currentSectorIndex
    if sector_index != DRIVER.sector:
        DRIVER.sector = sector_index
    DRIVER.laps_counter = info.graphics.numberOfLaps
    DRIVER.last_sector_time = info.graphics.lastSectorTime
