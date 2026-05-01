# utils/hotkeys.py
import threading
import time
from typing import Optional, Callable, Dict
from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    """Типы действий, которые можно привязать к клавишам"""
    START_ALL = "start_all"  # Начать фарм всего
    START_ONE = "start_one"  # Начать фарм конкретного ресурса
    STOP = "stop"  # Остановить фарм
    PAUSE = "pause"  # Пауза
    RESUME = "resume"  # Продолжить
    ADD_RECIPE = "add_recipe"  # Добавить ресурс
    EXIT = "exit"  # Выход из программы


@dataclass
class Hotkey:
    """Описывает одну горячую клавишу"""
    key: str  # Клавиша (например, "F6", "ctrl+1")
    action: ActionType  # Что делать
    arg: Optional[str] = None  # Аргумент (например, имя ресурса для start_one)
    description: str = ""  # Описание для справки


class HotkeyManager:
    """
    Менеджер глобальных горячих клавиш.

    Работает в отдельном потоке, слушает нажатия и вызывает callback'и.
    """

    def __init__(self):
        self.hotkeys: Dict[str, Hotkey] = {}
        self.callbacks: Dict[ActionType, Callable] = {}
        self.listener_thread: Optional[threading.Thread] = None
        self.running = False
        self._keyboard_available = False

        # Попытка импортировать keyboard
        self._init_keyboard()

    def _init_keyboard(self):
        """Инициализация библиотеки keyboard"""
        try:
            import keyboard
            self.keyboard = keyboard
            self._keyboard_available = True
        except ImportError:
            print("⚠️ Библиотека keyboard не установлена. Горячие клавиши не будут работать.")
            print("   Установите: pip install keyboard")

    def register_hotkey(self, hotkey: Hotkey):
        """
        Зарегистрировать горячую клавишу.

        Args:
            hotkey: Объект Hotkey с настройками
        """
        if not self._keyboard_available:
            return

        self.hotkeys[hotkey.key] = hotkey

        # Регистрируем в библиотеке keyboard
        try:
            self.keyboard.add_hotkey(hotkey.key, self._on_hotkey_pressed, args=(hotkey,))
            print(f"⌨️ Зарегистрирована клавиша: {hotkey.key} - {hotkey.description or hotkey.action.value}")
        except Exception as e:
            print(f"⚠️ Ошибка регистрации клавиши {hotkey.key}: {e}")

    def unregister_hotkey(self, key: str):
        """Удалить горячую клавишу"""
        if not self._keyboard_available:
            return

        if key in self.hotkeys:
            try:
                self.keyboard.remove_hotkey(key)
                del self.hotkeys[key]
            except Exception as e:
                print(f"⚠️ Ошибка удаления клавиши {key}: {e}")

    def _on_hotkey_pressed(self, hotkey: Hotkey):
        """Вызывается при нажатии зарегистрированной клавиши"""
        # Вызываем callback, если он зарегистрирован для этого действия
        if hotkey.action in self.callbacks:
            callback = self.callbacks[hotkey.action]
            try:
                if hotkey.arg:
                    callback(hotkey.arg)
                else:
                    callback()
            except Exception as e:
                print(f"⚠️ Ошибка в обработчике клавиши {hotkey.key}: {e}")

    def set_callback(self, action: ActionType, callback: Callable):
        """
        Установить callback для действия.

        Args:
            action: Тип действия
            callback: Функция, которая будет вызвана
        """
        self.callbacks[action] = callback

    def start_listening(self):
        """Запустить прослушивание горячих клавиш (в отдельном потоке)"""
        if not self._keyboard_available:
            print("⚠️ Горячие клавиши недоступны")
            return

        if self.running:
            return

        self.running = True

        # Слушаем в отдельном потоке, чтобы не блокировать основную программу
        self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listener_thread.start()
        print("🎹 Глобальные горячие клавиши активированы")

    def _listen_loop(self):
        """Основной цикл прослушивания (работает в потоке)"""
        try:
            # keyboard.wait() блокирует, но мы хотим не блокировать
            # Поэтому используем keyboard.on_press в режиме callback
            pass  # Регистрация уже сделана через add_hotkey
        except Exception as e:
            print(f"⚠️ Ошибка в цикле прослушивания: {e}")

    def stop_listening(self):
        """Остановить прослушивание"""
        self.running = False
        if self._keyboard_available:
            try:
                # Удаляем все зарегистрированные хоткеи
                for key in list(self.hotkeys.keys()):
                    self.unregister_hotkey(key)
                print("🎹 Горячие клавиши деактивированы")
            except Exception as e:
                print(f"⚠️ Ошибка при остановке: {e}")

    def get_help_text(self) -> str:
        """Возвращает текст справки по горячим клавишам"""
        if not self.hotkeys:
            return "   Нет зарегистрированных горячих клавиш"

        lines = []
        for hotkey in self.hotkeys.values():
            desc = hotkey.description or hotkey.action.value
            lines.append(f"   {hotkey.key:15} - {desc}")
        return "\n".join(lines)


def create_default_hotkeys() -> list:
    """
    Создаёт набор горячих клавиш по умолчанию.
    """
    return [
        Hotkey("F6", ActionType.START_ALL, description="Старт фарма всех ресурсов"),
        Hotkey("F7", ActionType.STOP, description="Остановка фарма"),
        Hotkey("F8", ActionType.PAUSE, description="Пауза"),
        Hotkey("F9", ActionType.RESUME, description="Продолжить"),
        Hotkey("ctrl+a", ActionType.ADD_RECIPE, description="Добавить ресурс (из игры)"),
        Hotkey("ctrl+q", ActionType.EXIT, description="Выход из программы"),
    ]


# Пример использования (для теста)
if __name__ == "__main__":
    """
    Тестирование горячих клавиш.
    Запустите этот файл отдельно для проверки.
    """
    print("=== Тест горячих клавиш ===")
    print("Нажмите F6, F7, Ctrl+Q для выхода")


    def on_start_all():
        print("🔥 F6 нажата — запускаем фарм всех!")


    def on_stop():
        print("🛑 F7 нажата — останавливаем фарм!")


    def on_exit():
        print("👋 Выход...")
        manager.stop_listening()
        exit(0)


    manager = HotkeyManager()

    # Регистрируем горячие клавиши
    for hotkey in create_default_hotkeys():
        manager.register_hotkey(hotkey)

    # Устанавливаем callback'и
    manager.set_callback(ActionType.START_ALL, on_start_all)
    manager.set_callback(ActionType.STOP, on_stop)
    manager.set_callback(ActionType.EXIT, on_exit)

    # Запускаем
    manager.start_listening()

    # Держим программу живой
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nПрограмма прервана")
