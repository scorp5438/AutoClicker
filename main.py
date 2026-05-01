# main.py
import os
import sys
import json
import threading
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.recipe_manager import RecipeManager
from core.clicker import AutoClicker
from utils.hotkeys import HotkeyManager, ActionType, create_default_hotkeys


def clear_console():
    """Очистка консоли (работает на Windows и Linux/Mac)"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Печать шапки программы"""
    print("=" * 50)
    print("        AUTO CLICKER v1.0")
    print("=" * 50)
    print()


def print_recipes(manager):
    """Показать список рецептов с их статусом"""
    recipes = manager.get_all_recipes()

    if not recipes:
        print("❌ Нет добавленных ресурсов.")
        print("   Используйте [A] чтобы добавить первый ресурс.")
        return

    print("📦 Доступные ресурсы:")
    for i, recipe in enumerate(recipes, 1):
        status = "✓ ВКЛ" if recipe.enabled else "✗ ВЫКЛ"
        print(f"  {i}. {recipe.name:15} [{status}]  пауза: {recipe.pause}с")
    print()


def print_hotkeys_help():
    """Печать справки по горячим клавишам"""
    print("🎹 Горячие клавиши (работают из любой программы):")
    print("   F6     - Старт фарма всех ресурсов")
    print("   F7     - Остановка фарма")
    print("   F8     - Пауза")
    print("   F9     - Продолжить")
    print("   Ctrl+A - Добавить ресурс (из игры)")
    print("   Ctrl+Q - Выход из программы")
    print()


def setup_hotkeys(hotkey_manager: HotkeyManager, clicker: AutoClicker,
                  recipe_manager: RecipeManager, main_menu_func):
    """
    Настройка горячих клавиш и их обработчиков.

    Args:
        hotkey_manager: Менеджер горячих клавиш
        clicker: Экземпляр автокликера
        recipe_manager: Менеджер рецептов
        main_menu_func: Функция для возврата в главное меню (опционально)
    """

    def on_start_all():
        """Обработчик: старт фарма всех ресурсов"""
        print("\n" + "=" * 50)
        print("🔥 ГОРЯЧАЯ КЛАВИША: Запуск фарма всех ресурсов")
        print("=" * 50)
        clicker.start_farming_all()

    def on_stop():
        """Обработчик: остановка фарма"""
        print("\n🛑 ГОРЯЧАЯ КЛАВИША: Остановка фарма")
        clicker.stop()

    def on_pause():
        """Обработчик: пауза"""
        print("\n⏸️ ГОРЯЧАЯ КЛАВИША: Пауза")
        clicker.pause()

    def on_resume():
        """Обработчик: продолжение"""
        print("\n▶️ ГОРЯЧАЯ КЛАВИША: Продолжение")
        clicker.resume()

    def on_add_recipe():
        """Обработчик: добавление рецепта прямо из игры"""
        print("\n" + "=" * 50)
        print("📦 ГОРЯЧАЯ КЛАВИША: Добавление нового ресурса")
        print("=" * 50)
        print("⚠️  Внимание! Сейчас будет добавлен новый ресурс.")
        print("    Переключитесь обратно в игру и наведите мышь на объект.")
        print()

        # Небольшая задержка, чтобы пользователь успел переключиться
        import time
        for i in range(3, 0, -1):
            print(f"   Захват через {i} секунд...")
            time.sleep(1)

        recipe_manager.add_recipe_interactive()
        print("\n✅ Возврат в режим ожидания...")

    def on_exit():
        """Обработчик: выход из программы"""
        print("\n👋 ГОРЯЧАЯ КЛАВИША: Выход из программы")
        clicker.stop()
        hotkey_manager.stop_listening()
        print("До свидания!")
        os._exit(0)

    # Регистрируем обработчики
    hotkey_manager.set_callback(ActionType.START_ALL, on_start_all)
    hotkey_manager.set_callback(ActionType.STOP, on_stop)
    hotkey_manager.set_callback(ActionType.PAUSE, on_pause)
    hotkey_manager.set_callback(ActionType.RESUME, on_resume)
    hotkey_manager.set_callback(ActionType.ADD_RECIPE, on_add_recipe)
    hotkey_manager.set_callback(ActionType.EXIT, on_exit)

    # Регистрируем стандартные горячие клавиши
    for hotkey in create_default_hotkeys():
        hotkey_manager.register_hotkey(hotkey)

    # Запускаем прослушивание
    hotkey_manager.start_listening()


def main_menu():
    """Главное меню"""
    manager = RecipeManager()
    clicker = AutoClicker(manager)

    # Настройка горячих клавиш
    hotkey_manager = HotkeyManager()
    setup_hotkeys(hotkey_manager, clicker, manager, main_menu)

    # Передаём hotkey_manager в clicker для возможности управления
    clicker.set_hotkey_manager(hotkey_manager)

    while True:
        clear_console()
        print_header()
        print_hotkeys_help()
        print_recipes(manager)

        print("Действия:")
        print("  [A] Добавить новый ресурс")
        print("  [D] Удалить ресурс")
        print("  [E] Включить/Выключить ресурс")
        print("  [P] Изменить паузу для ресурса")
        print("  [H] Показать горячие клавиши")
        print("  [L] Показать все рецепты заново")
        print("  [1-9] Старт фарма с выбранным ресурсом")
        print("  [S] Старт фарма (все включенные ресурсы)")
        print("  [Q] Выход")
        print()

        choice = input("Ваш выбор: ").strip().lower()

        if choice == 'a':
            clear_console()
            manager.add_recipe_interactive()
            input("\nНажмите Enter чтобы продолжить...")

        elif choice == 'd':
            clear_console()
            manager.delete_recipe_interactive()
            input("\nНажмите Enter чтобы продолжить...")

        elif choice == 'e':
            clear_console()
            manager.toggle_recipe_interactive()
            input("\nНажмите Enter чтобы продолжить...")

        elif choice == 'p':
            clear_console()
            manager.change_pause_interactive()
            input("\nНажмите Enter чтобы продолжить...")

        elif choice == 'h':
            clear_console()
            print_header()
            print_hotkeys_help()
            input("\nНажмите Enter чтобы продолжить...")

        elif choice == 'l':
            continue  # просто обновит экран

        elif choice == 's':
            clear_console()
            print("🌍 Запускаем фарм всех включенных ресурсов...")
            print("   Управление: F7 - стоп, F8 - пауза, F9 - продолжить")
            print()
            clicker.start_farming_all()
            input("\nНажмите Enter чтобы продолжить...")

        elif choice.isdigit():
            idx = int(choice) - 1
            recipes = manager.get_all_recipes()
            if 0 <= idx < len(recipes):
                clear_console()
                recipe = recipes[idx]
                print(f"🌲 Запускаем фарм ресурса: {recipe.name}")
                print("   Управление: F7 - стоп, F8 - пауза, F9 - продолжить")
                print()
                clicker.start_farming_one(recipe.name)
                input("\nНажмите Enter чтобы продолжить...")
            else:
                print("❌ Неверный номер ресурса")
                input("\nНажмите Enter...")

        elif choice == 'q':
            print("Выход...")
            hotkey_manager.stop_listening()
            break

        else:
            print("❌ Неверная команда")
            input("Нажмите Enter...")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
        input("Нажмите Enter для выхода...")
