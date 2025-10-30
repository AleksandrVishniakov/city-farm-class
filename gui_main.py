import logging
import sys
from datetime import datetime, time

from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QGridLayout, QGroupBox, QLabel,
                             QPushButton, QTabWidget, QSpinBox, QTimeEdit,
                             QProgressBar,
                             QMessageBox, QFrame, QSplitter, QCheckBox,
                             QDialog, QDialogButtonBox)
# Импортируем менеджер оборудования
from hardware_manager import hardware

from city_farm_class import setup_devices, read_file, write_file, \
    set_sensor_override, get_sensor_override
# Импортируем твои модули
from config.config import Pins
from devices.devices import Lamp, Pump, Doser
from devices.sensors import *

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Используем модули из hardware_manager
GPIO = hardware['GPIO']
DHT22 = hardware['DHT22']
Serial = hardware['Serial']
busio = type('Busio', (), {'I2C': hardware['I2C']})()
ADS = hardware['ADS1115']
AnalogIn = hardware['AnalogIn']
read_from_pwm = hardware['read_from_pwm']
IS_EMULATION = hardware['is_emulation']


class SensorOverrideDialog(QDialog):
    def __init__(self, sensor_name, parent=None):
        super().__init__(parent)
        self.sensor_name = sensor_name
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Подтверждение отключения датчика")
        self.setModal(True)
        self.setFixedSize(400, 200)

        layout = QVBoxLayout()

        # Предупреждающее сообщение
        warning_label = QLabel(
            f"<b>Внимание! Вы собираетесь отключить датчик {self.sensor_name}.</b><br><br>"
            "Это может привести к:<br>"
            "• Некорректной работе системы<br>"
            "• Возможному повреждению оборудования<br>"
            "• Безопасностным рискам<br><br>"
            "Продолжайте только если уверены в своих действиях."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: red;")

        # Чекбокс подтверждения
        self.confirm_check = QCheckBox("Я понимаю риски и хочу продолжить")

        # Кнопки
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Ok).setEnabled(False)

        # Связываем чекбокс с кнопкой OK
        self.confirm_check.toggled.connect(
            button_box.button(QDialogButtonBox.Ok).setEnabled
        )

        layout.addWidget(warning_label)
        layout.addWidget(self.confirm_check)
        layout.addWidget(button_box)
        self.setLayout(layout)


class SensorThread(QThread):
    data_updated = pyqtSignal(dict)

    def __init__(self, sensors_lifecycle):
        super().__init__()
        self.sensors = sensors_lifecycle
        self.running = True

    def run(self):
        while self.running:
            try:
                state = self.sensors.get_state()
                sensor_data = {
                    'temperature': state.temperature,
                    'humidity': state.humidity,
                    'co2': state.co2,
                    'ph': state.ph,
                    'ec': state.ec,
                    'water_level': state.water_value_dis,
                    'block_water': state.block_water
                }
                self.data_updated.emit(sensor_data)
                self.msleep(2000)  # Обновление каждые 2 секунды
            except Exception as e:
                logger.error(f"Ошибка в потоке датчиков: {e}")

    def stop(self):
        self.running = False


class DeviceControlWidget(QGroupBox):
    def __init__(self, device, name, parent=None):
        super().__init__(name, parent)
        self.device = device
        self.name = name
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.status_label = QLabel("Статус: Выключено")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")

        self.toggle_btn = QPushButton("Включить")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.clicked.connect(self.toggle_device)

        layout.addWidget(self.status_label)
        layout.addWidget(self.toggle_btn)
        self.setLayout(layout)

    def toggle_device(self, checked):
        if checked:
            self.device.on()
            self.status_label.setText("Статус: Включено")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.toggle_btn.setText("Выключить")
        else:
            self.device.off()
            self.status_label.setText("Статус: Выключено")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.toggle_btn.setText("Включить")

    def update_status(self):
        is_working = self.device.is_working()
        self.toggle_btn.setChecked(is_working)
        if is_working:
            self.status_label.setText("Статус: Включено")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.toggle_btn.setText("Выключить")
        else:
            self.status_label.setText("Статус: Выключено")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.toggle_btn.setText("Включить")


class SensorDisplayWidget(QGroupBox):
    def __init__(self, title, unit="", parent=None):
        super().__init__(title, parent)
        self.unit = unit
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.value_label = QLabel("--")
        self.value_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.value_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.value_label)
        self.setLayout(layout)

    def set_value(self, value):
        if value is not None:
            self.value_label.setText(f"{value} {self.unit}")

            # Цветовая индикация в зависимости от значений
            if "°C" in self.unit:
                if value > 30:
                    self.value_label.setStyleSheet("color: red;")
                elif value < 15:
                    self.value_label.setStyleSheet("color: blue;")
                else:
                    self.value_label.setStyleSheet("color: green;")
            elif "ppm" in self.unit:
                if value > 1000:
                    self.value_label.setStyleSheet("color: red;")
                else:
                    self.value_label.setStyleSheet("color: green;")
            elif "pH" in self.unit:
                if 5.5 <= value <= 6.5:
                    self.value_label.setStyleSheet("color: green;")
                else:
                    self.value_label.setStyleSheet("color: orange;")
        else:
            self.value_label.setText("--")
            self.value_label.setStyleSheet("color: gray;")


class HydroPonicGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.auto_mode = False
        self.settings = read_file()

        # Настройки отключения датчиков
        self.sensor_overrides = {
            'water_sensor': False,
            'temperature_sensor': False,
            'ph_sensor': False,
            'ec_sensor': False
        }

        self.init_devices()
        self.init_sensors()
        self.init_ui()
        self.setup_sensor_thread()

    def init_devices(self):
        """Инициализация устройств"""
        GPIO.setmode(GPIO.BCM)

        self.lamp = Lamp(Pins.LAMP)
        self.pump = Pump(Pins.PUMP)
        self.dozers = [
            Doser(Pins.DOSER_1),
            Doser(Pins.DOSER_2),
            Doser(Pins.DOSER_3),
            Doser(Pins.DOSER_4)
        ]

        setup_devices([self.lamp, self.pump] + self.dozers)

    def init_sensors(self):
        """Инициализация сенсоров"""
        try:
            self.dht_wrapper = DHTSensorWrapper(pin=Pins.DHT)

            # Инициализация I2C и ADS1115
            i2c = busio.I2C(board.SCL, board.SDA)
            ads = ADS.ADS1115(i2c)

            # Настройка водных сенсоров
            GPIO.setup(Pins.WATER_LOW_SENSOR, GPIO.OUT,
                       pull_up_down=GPIO.PUD_UP)
            GPIO.setup(Pins.WATER_HIGH_SENSOR, GPIO.OUT,
                       pull_up_down=GPIO.PUD_UP)

            low_water_sensor = WaterSensor(Pins.WATER_LOW_SENSOR)
            high_water_sensor = WaterSensor(Pins.WATER_HIGH_SENSOR)

            # Создание сенсоров
            temp_sensor = TemperatureSensor(self.dht_wrapper)
            hum_sensor = HumiditySensor(self.dht_wrapper)
            co2_sensor = CO2Sensor()
            ph_sensor = PHSensor(ads)
            ec_sensor = ECSensor(ads)

            self.sensors = SensorsLifecycle(
                temp=temp_sensor,
                hum=hum_sensor,
                co2=co2_sensor,
                ph=ph_sensor,
                ec=ec_sensor,
                low_ws=low_water_sensor,
                high_ws=high_water_sensor,
            )

            self.sensors.start(interval=2)
            self.sensors_state = self.sensors.get_state()

            # Подписка на изменения датчика воды
            @self.sensors_state.subscribe("on_change:block_water")
            def handle_water_block_change(value):
                # Останавливаем помпу только если датчик воды не отключен
                if not get_sensor_override('water_sensor') and not value:
                    self.pump.off()
                    logger.info("Помпа отключена по сигналу датчика воды")

        except Exception as e:
            logger.error(f"Ошибка инициализации сенсоров: {e}")
            self.sensors = None
            self.sensors_state = None

    def setup_sensor_thread(self):
        """Запуск потока для обновления данных сенсоров"""
        if self.sensors_state:
            self.sensor_thread = SensorThread(self.sensors)
            self.sensor_thread.data_updated.connect(self.update_sensor_display)
            self.sensor_thread.start()

    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle(
            "Гидропонная установка - Панель управления (PyQt5)")
        self.setGeometry(100, 100, 1200, 800)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Верхняя панель с общей информацией
        main_layout.addWidget(self.create_status_bar())

        # Splitter для разделения на левую и правую части
        splitter = QSplitter(Qt.Horizontal)

        # Левая часть - мониторинг
        left_widget = self.create_monitoring_panel()
        splitter.addWidget(left_widget)

        # Правая часть - управление
        right_widget = self.create_control_panel()
        splitter.addWidget(right_widget)

        splitter.setSizes([600, 400])
        main_layout.addWidget(splitter)

        # Таймер для обновления UI
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_ui)
        self.ui_timer.start(1000)  # Обновление каждую секунду

    def create_status_bar(self):
        """Создание верхней панели статуса"""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel)
        status_frame.setStyleSheet("background-color: #f0f0f0; padding: 10px;")

        layout = QHBoxLayout()

        # Время
        self.time_label = QLabel()
        self.time_label.setFont(QFont("Arial", 12))

        # Режим работы
        self.mode_label = QLabel("Ручной режим")
        self.mode_label.setStyleSheet("color: orange; font-weight: bold;")

        # Статус датчиков
        sensor_status = "Датчики: "
        if any(self.sensor_overrides.values()):
            sensor_status += "⚠ Некоторые отключены"
            self.sensor_status_label = QLabel(sensor_status)
            self.sensor_status_label.setStyleSheet(
                "color: red; font-weight: bold;")
        else:
            sensor_status += "✓ Активны"
            self.sensor_status_label = QLabel(sensor_status)
            self.sensor_status_label.setStyleSheet("color: green;")

        # Кнопка переключения режима
        self.auto_btn = QPushButton("Включить авторежим")
        self.auto_btn.setCheckable(True)
        self.auto_btn.clicked.connect(self.toggle_auto_mode)

        layout.addWidget(QLabel("Время:"))
        layout.addWidget(self.time_label)
        layout.addStretch()
        layout.addWidget(self.sensor_status_label)
        layout.addWidget(self.mode_label)
        layout.addWidget(self.auto_btn)

        status_frame.setLayout(layout)
        return status_frame

    def create_monitoring_panel(self):
        """Создание панели мониторинга"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("Мониторинг системы")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)

        # Сенсоры в виде сетки
        sensors_grid = QGridLayout()

        self.temp_sensor = SensorDisplayWidget("Температура", "°C")
        self.hum_sensor = SensorDisplayWidget("Влажность", "%")
        self.co2_sensor = SensorDisplayWidget("CO2", "ppm")
        self.ph_sensor = SensorDisplayWidget("pH", "pH")
        self.ec_sensor = SensorDisplayWidget("EC", "µS/cm")

        sensors_grid.addWidget(self.temp_sensor, 0, 0)
        sensors_grid.addWidget(self.hum_sensor, 0, 1)
        sensors_grid.addWidget(self.co2_sensor, 1, 0)
        sensors_grid.addWidget(self.ph_sensor, 1, 1)
        sensors_grid.addWidget(self.ec_sensor, 2, 0)

        layout.addLayout(sensors_grid)

        # Прогресс бар уровня воды
        water_group = QGroupBox("Уровень воды")
        water_layout = QVBoxLayout()

        self.water_level_bar = QProgressBar()
        self.water_level_bar.setRange(0, 100)
        self.water_level_bar.setTextVisible(True)
        self.water_level_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 20px;
            }
        """)

        self.water_status_label = QLabel("Статус: Норма")

        # Кнопка отключения датчика воды
        self.water_sensor_override_btn = QPushButton(
            "Отключить защиту по воде")
        self.water_sensor_override_btn.setCheckable(True)
        self.water_sensor_override_btn.setStyleSheet(
            "QPushButton:checked { background-color: red; color: white; }")
        self.water_sensor_override_btn.toggled.connect(
            lambda checked: self.toggle_sensor_override('water_sensor',
                                                        checked,
                                                        "датчика воды")
        )

        water_layout.addWidget(self.water_level_bar)
        water_layout.addWidget(self.water_status_label)
        water_layout.addWidget(self.water_sensor_override_btn)
        water_group.setLayout(water_layout)

        layout.addWidget(water_group)
        layout.addStretch()

        widget.setLayout(layout)
        return widget

    def create_control_panel(self):
        """Создание панели управления"""
        tab_widget = QTabWidget()

        # Вкладка устройств
        tab_widget.addTab(self.create_devices_tab(), "Устройства")

        # Вкладка настроек
        tab_widget.addTab(self.create_settings_tab(), "Настройки")

        # Вкладка дозаторов
        tab_widget.addTab(self.create_dosers_tab(), "Дозаторы")

        # Вкладка отладки датчиков
        tab_widget.addTab(self.create_sensor_debug_tab(), "Отладка датчиков")

        return tab_widget

    def create_devices_tab(self):
        """Вкладка управления устройствами"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Лампа
        self.lamp_control = DeviceControlWidget(self.lamp, "Освещение")
        layout.addWidget(self.lamp_control)

        # Помпа
        pump_group = QGroupBox("Помпа")
        pump_layout = QVBoxLayout()

        self.pump_control = DeviceControlWidget(self.pump, "")
        pump_layout.addWidget(self.pump_control)

        # Предупреждение если отключен датчик воды
        self.pump_warning_label = QLabel("")
        self.pump_warning_label.setStyleSheet(
            "color: orange; font-weight: bold;")
        self.pump_warning_label.setVisible(False)
        pump_layout.addWidget(self.pump_warning_label)

        pump_group.setLayout(pump_layout)
        layout.addWidget(pump_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_dosers_tab(self):
        """Вкладка управления дозаторами"""
        widget = QWidget()
        layout = QGridLayout()

        self.doser_controls = []
        for i, doser in enumerate(self.dozers):
            doser_control = DeviceControlWidget(doser, f"Дозатор {i + 1}")
            self.doser_controls.append(doser_control)
            layout.addWidget(doser_control, i // 2, i % 2)

        widget.setLayout(layout)
        return widget

    def create_settings_tab(self):
        """Вкладка настроек"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Настройки освещения
        light_group = QGroupBox("Настройки освещения")
        light_layout = QGridLayout()

        light_layout.addWidget(QLabel("Включение:"), 0, 0)
        self.light_on_time = QTimeEdit()
        self.light_on_time.setTime(
            time.fromisoformat(self.settings['lamp_set'][0]))
        light_layout.addWidget(self.light_on_time, 0, 1)

        light_layout.addWidget(QLabel("Выключение:"), 1, 0)
        self.light_off_time = QTimeEdit()
        self.light_off_time.setTime(
            time.fromisoformat(self.settings['lamp_set'][1]))
        light_layout.addWidget(self.light_off_time, 1, 1)

        light_group.setLayout(light_layout)
        layout.addWidget(light_group)

        # Настройки полива
        water_group = QGroupBox("Настройки полива")
        water_layout = QGridLayout()

        water_layout.addWidget(QLabel("Полив днем:"), 0, 0)
        self.water_day = QSpinBox()
        self.water_day.setRange(0, 10)
        self.water_day.setValue(self.settings['water_day'])
        water_layout.addWidget(self.water_day, 0, 1)

        water_layout.addWidget(QLabel("Полив ночью:"), 1, 0)
        self.water_night = QSpinBox()
        self.water_night.setRange(0, 10)
        self.water_night.setValue(self.settings['water_night'])
        water_layout.addWidget(self.water_night, 1, 1)

        water_layout.addWidget(QLabel("Время полива (мин):"), 2, 0)
        self.water_duration = QSpinBox()
        self.water_duration.setRange(1, 60)
        self.water_duration.setValue(self.settings['time_water'])
        water_layout.addWidget(self.water_duration, 2, 1)

        water_group.setLayout(water_layout)
        layout.addWidget(water_group)

        # Кнопки управления настройками
        btn_layout = QHBoxLayout()

        save_btn = QPushButton("Сохранить настройки")
        save_btn.clicked.connect(self.save_settings)

        load_btn = QPushButton("Загрузить настройки")
        load_btn.clicked.connect(self.load_settings)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(load_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

        widget.setLayout(layout)
        return widget

    def create_sensor_debug_tab(self):
        """Вкладка отладки и управления датчиками"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("Управление датчиками")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)

        info_label = QLabel(
            "Внимание: Отключение датчиков может привести к некорректной работе системы "
            "и возможному повреждению оборудования. Используйте только для отладки!"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            "color: red; background-color: #ffe6e6; padding: 10px; border-radius: 5px;")
        layout.addWidget(info_label)

        # Чекбоксы отключения датчиков
        sensors_group = QGroupBox("Отключение датчиков")
        sensors_layout = QVBoxLayout()

        self.water_sensor_check = QCheckBox("Отключить защиту по датчику воды")
        self.water_sensor_check.toggled.connect(
            lambda checked: self.toggle_sensor_override('water_sensor',
                                                        checked,
                                                        "датчика воды")
        )

        self.temp_sensor_check = QCheckBox(
            "Игнорировать показания температуры")
        self.temp_sensor_check.toggled.connect(
            lambda checked: self.toggle_sensor_override('temperature_sensor',
                                                        checked, "температуры")
        )

        self.ph_sensor_check = QCheckBox("Игнорировать показания pH")
        self.ph_sensor_check.toggled.connect(
            lambda checked: self.toggle_sensor_override('ph_sensor', checked,
                                                        "pH")
        )

        self.ec_sensor_check = QCheckBox("Игнорировать показания EC")
        self.ec_sensor_check.toggled.connect(
            lambda checked: self.toggle_sensor_override('ec_sensor', checked,
                                                        "EC")
        )

        sensors_layout.addWidget(self.water_sensor_check)
        sensors_layout.addWidget(self.temp_sensor_check)
        sensors_layout.addWidget(self.ph_sensor_check)
        sensors_layout.addWidget(self.ec_sensor_check)
        sensors_group.setLayout(sensors_layout)

        layout.addWidget(sensors_group)
        layout.addStretch()

        # Кнопка сброса всех отключений
        reset_btn = QPushButton("Включить все датчики")
        reset_btn.clicked.connect(self.reset_sensor_overrides)
        reset_btn.setStyleSheet(
            "background-color: green; color: white; font-weight: bold;")
        layout.addWidget(reset_btn)

        widget.setLayout(layout)
        return widget

    def toggle_sensor_override(self, sensor_type, checked, sensor_name):
        """Включение/отключение датчика с подтверждением"""
        if checked:
            dialog = SensorOverrideDialog(sensor_name, self)
            if dialog.exec() == QDialog.Accepted:
                self.sensor_overrides[sensor_type] = True
                set_sensor_override(sensor_type,
                                    True)  # Устанавливаем в основном коде
                logger.warning(f"Датчик {sensor_name} отключен пользователем")

                # Обновление UI
                if sensor_type == 'water_sensor':
                    self.water_sensor_override_btn.setChecked(True)
                    self.water_sensor_override_btn.setText(
                        "Защита по воде ОТКЛЮЧЕНА")
                    self.pump_warning_label.setText(
                        "⚠ Защита по воде отключена!")
                    self.pump_warning_label.setVisible(True)
            else:
                # Пользователь отменил - сбрасываем чекбокс
                if sensor_type == 'water_sensor':
                    self.water_sensor_check.setChecked(False)
                    self.water_sensor_override_btn.setChecked(False)
                elif sensor_type == 'temperature_sensor':
                    self.temp_sensor_check.setChecked(False)
                elif sensor_type == 'ph_sensor':
                    self.ph_sensor_check.setChecked(False)
                elif sensor_type == 'ec_sensor':
                    self.ec_sensor_check.setChecked(False)
        else:
            self.sensor_overrides[sensor_type] = False
            set_sensor_override(sensor_type,
                                False)  # Отключаем в основном коде
            logger.info(f"Датчик {sensor_name} включен")

            # Обновление UI
            if sensor_type == 'water_sensor':
                self.water_sensor_override_btn.setChecked(False)
                self.water_sensor_override_btn.setText(
                    "Отключить защиту по воде")
                self.pump_warning_label.setVisible(False)

        self.update_sensor_status()

    def reset_sensor_overrides(self):
        """Включение всех датчиков"""
        self.sensor_overrides = {key: False for key in self.sensor_overrides}

        # Сброс в основном коде
        for sensor_type in self.sensor_overrides:
            set_sensor_override(sensor_type, False)

        # Сброс UI
        self.water_sensor_check.setChecked(False)
        self.temp_sensor_check.setChecked(False)
        self.ph_sensor_check.setChecked(False)
        self.ec_sensor_check.setChecked(False)
        self.water_sensor_override_btn.setChecked(False)
        self.water_sensor_override_btn.setText("Отключить защиту по воде")
        self.pump_warning_label.setVisible(False)

        self.update_sensor_status()
        logger.info("Все датчики включены")
        QMessageBox.information(self, "Успех", "Все датчики включены!")

    def update_sensor_status(self):
        """Обновление статуса датчиков в верхней панели"""
        if any(self.sensor_overrides.values()):
            disabled_count = sum(self.sensor_overrides.values())
            self.sensor_status_label.setText(
                f"Датчики: ⚠ Отключено {disabled_count}")
            self.sensor_status_label.setStyleSheet(
                "color: red; font-weight: bold;")
        else:
            self.sensor_status_label.setText("Датчики: ✓ Активны")
            self.sensor_status_label.setStyleSheet("color: green;")

    def update_sensor_display(self, data):
        """Обновление отображения данных сенсоров"""
        # Игнорируем данные отключенных датчиков
        if not self.sensor_overrides['temperature_sensor']:
            self.temp_sensor.set_value(data['temperature'])
        else:
            self.temp_sensor.set_value(None)

        self.hum_sensor.set_value(data['humidity'])
        self.co2_sensor.set_value(data['co2'])

        if not self.sensor_overrides['ph_sensor']:
            self.ph_sensor.set_value(data['ph'])
        else:
            self.ph_sensor.set_value(None)

        if not self.sensor_overrides['ec_sensor']:
            self.ec_sensor.set_value(data['ec'])
        else:
            self.ec_sensor.set_value(None)

        # Обновление уровня воды (всегда показываем, даже если датчик отключен)
        water_level = data['water_level']
        self.water_level_bar.setValue(water_level)

        # Статус воды
        if self.sensor_overrides['water_sensor']:
            self.water_status_label.setText("Статус: ЗАЩИТА ОТКЛЮЧЕНА")
            self.water_status_label.setStyleSheet(
                "color: red; font-weight: bold;")
        elif water_level <= 20:
            self.water_status_label.setText("Статус: Низкий уровень!")
            self.water_status_label.setStyleSheet(
                "color: red; font-weight: bold;")
        elif water_level <= 50:
            self.water_status_label.setText("Статус: Средний уровень")
            self.water_status_label.setStyleSheet("color: orange;")
        else:
            self.water_status_label.setText("Статус: Норма")
            self.water_status_label.setStyleSheet("color: green;")

    def update_ui(self):
        """Обновление UI"""
        # Время
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.setText(current_time)

        # Обновление статусов устройств
        self.lamp_control.update_status()
        self.pump_control.update_status()

        for doser_control in self.doser_controls:
            doser_control.update_status()

    def toggle_auto_mode(self, checked):
        """Переключение режима автоматического управления"""
        self.auto_mode = checked

        if checked:
            self.mode_label.setText("Автоматический режим")
            self.mode_label.setStyleSheet("color: green; font-weight: bold;")
            self.auto_btn.setText("Выключить авторежим")

            # Блокировка ручного управления в авторежиме
            self.lamp_control.toggle_btn.setEnabled(False)
            self.pump_control.toggle_btn.setEnabled(False)
        else:
            self.mode_label.setText("Ручной режим")
            self.mode_label.setStyleSheet("color: orange; font-weight: bold;")
            self.auto_btn.setText("Включить авторежим")

            # Разблокировка ручного управления
            self.lamp_control.toggle_btn.setEnabled(True)
            self.pump_control.toggle_btn.setEnabled(True)

    def save_settings(self):
        """Сохранение настроек в файл"""
        try:
            new_settings = {
                "lamp_set": [
                    self.light_on_time.time().toString("hh:mm"),
                    self.light_off_time.time().toString("hh:mm")
                ],
                "water_day": self.water_day.value(),
                "water_night": self.water_night.value(),
                "time_water": self.water_duration.value()
            }

            write_file(new_settings)
            self.settings = new_settings

            QMessageBox.information(self, "Успех", "Настройки сохранены!")
            logger.info("Настройки сохранены")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка",
                                 f"Не удалось сохранить настройки: {e}")
            logger.error(f"Ошибка сохранения настроек: {e}")

    def load_settings(self):
        """Загрузка настроек из файла"""
        try:
            self.settings = read_file()

            # Обновление UI
            self.light_on_time.setTime(
                time.fromisoformat(self.settings['lamp_set'][0]))
            self.light_off_time.setTime(
                time.fromisoformat(self.settings['lamp_set'][1]))
            self.water_day.setValue(self.settings['water_day'])
            self.water_night.setValue(self.settings['water_night'])
            self.water_duration.setValue(self.settings['time_water'])

            QMessageBox.information(self, "Успех", "Настройки загружены!")
            logger.info("Настройки загружены")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка",
                                 f"Не удалось загрузить настройки: {e}")
            logger.error(f"Ошибка загрузки настроек: {e}")

    def closeEvent(self, event):
        """Обработка закрытия приложения"""
        # Предупреждение если отключены датчики
        if any(self.sensor_overrides.values()):
            reply = QMessageBox.warning(
                self, 'Внимание!',
                'У вас отключены некоторые датчики. Это может быть опасно для оборудования.\n\n'
                'Вы уверены, что хотите закрыть приложение?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
        else:
            reply = QMessageBox.question(
                self, 'Подтверждение',
                'Вы уверены, что хотите закрыть приложение?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

        if reply == QMessageBox.Yes:
            # Остановка потоков и очистка
            if hasattr(self, 'sensor_thread'):
                self.sensor_thread.stop()
                self.sensor_thread.wait(2000)

            GPIO.cleanup()
            event.accept()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv)

    # Установка стиля
    app.setStyle('Fusion')

    window = HydroPonicGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
