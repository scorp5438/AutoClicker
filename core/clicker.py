import time
import sys
from pathlib import Path
from typing import Optional, List
import threading

from models.recipe import Recipe
from core.recipe_manager import RecipeManager
from utils.screenshot import ScreenshotFinder, FoundObject


class AutoClicker:
    """
    Движок автокликера.
    Ищет ресурсы на экране по шаблону и кликает по ним.
    """

    def __init__(self, manager: RecipeManager):
        self.manager = manager
        self.running = False
        self.paused = False
        self.stop_key_pressed = False

        # Настройки поиска
        self.confidence = 0.8  # Уверенность совпадения (0.8 = 80%)
        self.search_interval = 0.3  # Интервал между поиском (сек)
        self.click_delay = 0.05  # Задержка перед кликом (имитация человека)

        # Случайные отклонения для кликов (анти-бан)
        self.random_offset = 5  # Пикселей ± от центра

        # Инициализируем модуль скриншотов
        self.finder = ScreenshotFinder()

        # Для глобальных хоткеев (будет установлен извне)
        self.hotkey_manager = None

    def set_hotkey_manager(self, hotkey_manager):
        """Устанавливает менеджер горячих клавиш"""
        self.hotkey_manager = hotkey_manager

    def click_at(self, x: int, y: int, randomize: bool = True):
        """
        Кликает в указанные координаты с возможным случайным смещением.

        Args:
            x, y: Центр цели
            randomize: Добавлять ли случайное смещение (анти-бан)
        """
        if not self.finder.libraries_ok:
            return

        try:
            # Добавляем случайное смещение (чтобы не кликать строго в центр)
            if randomize and self.random_offset > 0:
                import random
                offset_x = random.randint(-self.random_offset, self.random_offset)
                offset_y = random.randint(-self.random_offset, self.random_offset)
                click_x = x + offset_x
                click_y = y + offset_y
            else:
                click_x, click_y = x, y

            # Небольшая задержка перед кликом (имитация человека)
            if self.click_delay > 0:
                time.sleep(self.click_delay)

            self.finder.pyautogui.click(click_x, click_y)
            print(f"🖱️ Клик по ({click_x}, {click_y}) [цель: {x}, {y}]")
        except Exception as e:
            print(f"⚠️ Ошибка клика: {e}")

    def find_object_on_screen(self, template_path: Path) -> Optional[tuple]:
        """
        Ищет объект на экране по шаблону (обёртка для ScreenshotFinder).

        Args:
            template_path: Путь к картинке-образцу

        Returns:
            (x, y) координаты центра найденного объекта или None
        """
        found = self.finder.find_object(template_path, confidence=self.confidence)
        if found:
            return (found.x, found.y)
        return None

    def wait_for_stop_or_pause(self):
        """
        Ожидает нажатия клавиш в отдельном потоке.
        F7 - остановка, F8 - пауза, F9 - продолжить
        """
        if not self.finder.libraries_ok:
            return

        try:
            import keyboard
            while self.running:
                if keyboard.is_pressed('F7'):
                    self.running = False
                    print("\n🛑 Остановка по запросу (F7)")
                    break
                elif keyboard.is_pressed('F8'):
                    if not self.paused:
                        self.paused = True
                        print("\n⏸️ Пауза (F8). Нажмите F9 для продолжения")
                    while self.paused and self.running:
                        if keyboard.is_pressed('F9'):
                            self.paused = False
                            print("\n▶️ Продолжаем (F9)")
                            break
                        time.sleep(0.1)
                time.sleep(0.05)
        except:
            pass

    def start_farming_one(self, recipe_name: str):
        """
        Фармит один конкретный ресурс.

        Args:
            recipe_name: Имя ресурса (например, "wood")
        """
        recipe = self.manager.get_recipe(recipe_name)
        if not recipe:
            print(f"❌ Ресурс '{recipe_name}' не найден")
            return

        if not recipe.enabled:
            print(f"❌ Ресурс '{recipe_name}' выключен. Включите его в меню.")
            return

        if not self.finder.libraries_ok:
            print("❌ Библиотеки не загружены. Установите необходимые зависимости.")
            return

        self.running = True
        self.paused = False

        # Запускаем поток для отслеживания F7/F8/F9
        stop_thread = threading.Thread(target=self.wait_for_stop_or_pause, daemon=True)
        stop_thread.start()

        print(f"🌲 Начинаем фармить '{recipe.name}'")
        print(f"   Пауза после клика: {recipe.pause}с")
        print("   Управление: F7 - стоп, F8 - пауза, F9 - продолжить")

        click_count = 0
        not_found_count = 0
        max_not_found = 10  # После 10 неудачных поисков подряд завершаем

        while self.running:
            # Если на паузе - ждём
            if self.paused:
                time.sleep(0.1)
                continue

            try:
                # Ищем объект на экране
                pos = self.find_object_on_screen(recipe.template_path)

                if pos:
                    # Нашли - кликаем
                    self.click_at(pos[0], pos[1])
                    click_count += 1
                    not_found_count = 0  # Сбрасываем счётчик неудач
                    print(f"   [Добыто: {click_count}] Ждём {recipe.pause}с...")
                    time.sleep(recipe.pause)
                else:
                    # Не нашли
                    not_found_count += 1
                    if not_found_count >= max_not_found:
                        print(f"🔍 Объект '{recipe.name}' не найден после {max_not_found} попыток. Завершаем.")
                        break

                    if not_found_count % 3 == 1:  # Каждую 3-ю попытку пишем
                        print(f"🔍 Объект '{recipe.name}' не найден (попытка {not_found_count})...")

                    time.sleep(self.search_interval)

            except KeyboardInterrupt:
                print("\n🛑 Прерывание пользователем")
                break
            except Exception as e:
                print(f"⚠️ Ошибка в цикле: {e}")
                time.sleep(1)

        print(f"\n📊 Фарм завершён. Всего кликов: {click_count}")

    def start_farming_all(self):
        """
        Фармит все включённые ресурсы по очереди.
        Циклически проходится по enabled рецептам и ищет каждый.
        """
        enabled_recipes = self.manager.get_enabled_recipes()

        if not enabled_recipes:
            print("❌ Нет включённых ресурсов. Включите хотя бы один в меню.")
            return

        if not self.finder.libraries_ok:
            print("❌ Библиотеки не загружены. Установите необходимые зависимости.")
            return

        self.running = True
        self.paused = False

        # Запускаем поток для отслеживания F7/F8/F9
        stop_thread = threading.Thread(target=self.wait_for_stop_or_pause, daemon=True)
        stop_thread.start()

        print(f"🌍 Начинаем фарм всех включённых ресурсов ({len(enabled_recipes)} шт.)")
        print("   Управление: F7 - стоп, F8 - пауза, F9 - продолжить")

        click_count = 0
        recipe_index = 0

        while self.running:
            # Если на паузе - ждём
            if self.paused:
                time.sleep(0.1)
                continue

            try:
                # Берём следующий рецепт по кругу
                recipe = enabled_recipes[recipe_index % len(enabled_recipes)]
                recipe_index += 1

                # Ищем этот ресурс на экране
                pos = self.find_object_on_screen(recipe.template_path)

                if pos:
                    self.click_at(pos[0], pos[1])
                    click_count += 1
                    print(f"   [{recipe.name}] Добыто: {click_count} | Ждём {recipe.pause}с...")
                    time.sleep(recipe.pause)
                else:
                    # Быстро переключаемся на следующий ресурс
                    print(f"🔍 [{recipe.name}] не найден, переключаюсь...")
                    time.sleep(self.search_interval)

            except KeyboardInterrupt:
                print("\n🛑 Прерывание пользователем")
                break
            except Exception as e:
                print(f"⚠️ Ошибка: {e}")
                time.sleep(1)

        print(f"\n📊 Фарм всего завершён. Всего кликов: {click_count}")

    def stop(self):
        """Останавливает текущий фарм"""
        self.running = False
        self.paused = False
        print("\n🛑 Остановка фарма")

    def pause(self):
        """Ставит фарм на паузу"""
        if self.running and not self.paused:
            self.paused = True
            print("\n⏸️ Пауза")

    def resume(self):
        """Продолжает фарм после паузы"""
        if self.running and self.paused:
            self.paused = False
            print("\n▶️ Продолжение")
