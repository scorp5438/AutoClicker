# utils/screenshot.py
import time
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class FoundObject:
    """Результат поиска объекта на экране"""
    x: int  # Координата X центра
    y: int  # Координата Y центра
    confidence: float  # Уверенность совпадения (0-1)
    template_name: str  # Имя шаблона (для отладки)


class ScreenshotFinder:
    """
    Утилиты для работы со скриншотами и поиском объектов на экране.

    Возможности:
        - Поиск объекта по шаблону (OpenCV)
        - Захват шаблона под курсором
        - Поиск нескольких объектов одновременно
        - Обрезка области экрана для ускорения поиска
    """

    def __init__(self):
        self.libraries_ok = False
        self.cv2 = None
        self.np = None
        self.pyautogui = None
        self._init_libraries()

    def _init_libraries(self):
        """Ленивая загрузка библиотек"""
        try:
            import cv2
            import numpy as np
            import pyautogui
            self.cv2 = cv2
            self.np = np
            self.pyautogui = pyautogui
            self.pyautogui.PAUSE = 0
            self.libraries_ok = True
        except ImportError as e:
            print(f"⚠️ Ошибка импорта библиотек скриншотов: {e}")
            print("   Установите: pip install opencv-python pyautogui numpy")

    def capture_template_under_mouse(self, size: int = 50) -> Optional[Path]:
        """
        Захватывает область под курсором и сохраняет как шаблон.

        Args:
            size: Размер квадратной области (например, 50 = 50x50 пикселей)

        Returns:
            Путь к сохранённому изображению или None
        """
        if not self.libraries_ok:
            return None

        try:
            # Получаем позицию мыши
            x, y = self.pyautogui.position()

            # Вычисляем область
            left = x - size // 2
            top = y - size // 2

            # Делаем скриншот
            screenshot = self.pyautogui.screenshot(region=(left, top, size, size))

            # Создаём временный файл или возвращаем данные
            # (сохранением занимается вызывающий код)
            return screenshot

        except Exception as e:
            print(f"⚠️ Ошибка захвата шаблона: {e}")
            return None

    def capture_region(self, left: int, top: int, width: int, height: int):
        """
        Делает скриншот указанной области.

        Args:
            left, top: Координаты левого верхнего угла
            width, height: Ширина и высота области

        Returns:
            Изображение в формате numpy array (BGR для OpenCV)
        """
        if not self.libraries_ok:
            return None

        try:
            screenshot = self.pyautogui.screenshot(region=(left, top, width, height))
            return self.cv2.cvtColor(self.np.array(screenshot), self.cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"⚠️ Ошибка захвата области: {e}")
            return None

    def capture_fullscreen(self):
        """Делает скриншот всего экрана"""
        if not self.libraries_ok:
            return None

        try:
            screenshot = self.pyautogui.screenshot()
            return self.cv2.cvtColor(self.np.array(screenshot), self.cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"⚠️ Ошибка захвата экрана: {e}")
            return None

    def find_object(self, template_path: Path,
                    screen_image=None,
                    confidence: float = 0.8,
                    search_region: Optional[Tuple[int, int, int, int]] = None) -> Optional[FoundObject]:
        """
        Ищет один объект на экране по шаблону.

        Args:
            template_path: Путь к изображению-шаблону
            screen_image: Готовый скриншот (если None, делает новый)
            confidence: Минимальный порог уверенности (0.7-0.95)
            search_region: Ограничить поиск областью (left, top, width, height)

        Returns:
            FoundObject или None
        """
        if not self.libraries_ok:
            return None

        try:
            # Загружаем шаблон
            template = self.cv2.imread(str(template_path))
            if template is None:
                print(f"⚠️ Не удалось загрузить шаблон: {template_path}")
                return None

            # Получаем скриншот
            if screen_image is None:
                if search_region:
                    screen = self.capture_region(*search_region)
                else:
                    screen = self.capture_fullscreen()
            else:
                screen = screen_image

            if screen is None:
                return None

            # Ищем совпадение
            result = self.cv2.matchTemplate(screen, template, self.cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = self.cv2.minMaxLoc(result)

            if max_val >= confidence:
                h, w = template.shape[:2]
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2

                # Корректируем координаты, если искали в области
                if search_region:
                    center_x += search_region[0]
                    center_y += search_region[1]

                return FoundObject(
                    x=center_x,
                    y=center_y,
                    confidence=max_val,
                    template_name=Path(template_path).parent.name
                )

            return None

        except Exception as e:
            print(f"⚠️ Ошибка поиска объекта: {e}")
            return None

    def find_all_objects(self, templates: List[Tuple[Path, float]],
                         search_region: Optional[Tuple[int, int, int, int]] = None,
                         max_results: int = 10) -> List[FoundObject]:
        """
        Ищет несколько объектов на одном скриншоте (оптимизировано).

        Args:
            templates: Список пар (путь_к_шаблону, confidence)
            search_region: Ограничить поиск областью
            max_results: Максимум результатов

        Returns:
            Список найденных объектов (отсортирован по уверенности)
        """
        if not self.libraries_ok:
            return []

        try:
            # Делаем один скриншот для всех поисков
            if search_region:
                screen = self.capture_region(*search_region)
            else:
                screen = self.capture_fullscreen()

            if screen is None:
                return []

            results = []

            for template_path, confidence in templates:
                template = self.cv2.imread(str(template_path))
                if template is None:
                    continue

                result = self.cv2.matchTemplate(screen, template, self.cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = self.cv2.minMaxLoc(result)

                if max_val >= confidence:
                    h, w = template.shape[:2]
                    center_x = max_loc[0] + w // 2
                    center_y = max_loc[1] + h // 2

                    if search_region:
                        center_x += search_region[0]
                        center_y += search_region[1]

                    results.append(FoundObject(
                        x=center_x,
                        y=center_y,
                        confidence=max_val,
                        template_name=Path(template_path).parent.name
                    ))

            # Сортируем по уверенности (от лучших к худшим)
            results.sort(key=lambda r: r.confidence, reverse=True)
            return results[:max_results]

        except Exception as e:
            print(f"⚠️ Ошибка массового поиска: {e}")
            return []

    def save_screenshot(self, path: Path, region: Optional[Tuple[int, int, int, int]] = None):
        """
        Сохраняет скриншот в файл (для отладки).

        Args:
            path: Куда сохранить
            region: Область (left, top, width, height)
        """
        if not self.libraries_ok:
            return

        try:
            if region:
                screenshot = self.pyautogui.screenshot(region=region)
            else:
                screenshot = self.pyautogui.screenshot()
            screenshot.save(path)
            print(f"📸 Скриншот сохранён: {path}")
        except Exception as e:
            print(f"⚠️ Ошибка сохранения скриншота: {e}")

    def is_object_on_screen(self, template_path: Path, confidence: float = 0.8) -> bool:
        """
        Быстрая проверка: есть ли объект на экране.

        Returns:
            True если найден хотя бы с заданной уверенностью
        """
        found = self.find_object(template_path, confidence=confidence)
        return found is not None

    def wait_for_object(self, template_path: Path,
                        timeout: float = 30.0,
                        confidence: float = 0.8,
                        check_interval: float = 1.0) -> Optional[FoundObject]:
        """
        Ожидает появления объекта на экране.

        Args:
            template_path: Путь к шаблону
            timeout: Максимальное время ожидания в секундах
            confidence: Уверенность
            check_interval: Интервал между проверками

        Returns:
            FoundObject или None (таймаут)
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            found = self.find_object(template_path, confidence=confidence)
            if found:
                return found
            time.sleep(check_interval)

        return None


# Пример использования (для теста)
if __name__ == "__main__":
    """
    Тестирование функций скриншотов.
    Запустите этот файл отдельно для проверки.
    """
    import tempfile

    finder = ScreenshotFinder()

    if not finder.libraries_ok:
        print("❌ Библиотеки не установлены. Выполните: pip install opencv-python pyautogui numpy")
        exit(1)

    print("=== Тест скриншотов ===")

    # Тест 1: захват области под мышью
    print("\n1. Захват шаблона под курсором...")
    print("   Переместите мышь на какой-нибудь объект и нажмите Enter")
    input()

    screenshot = finder.capture_template_under_mouse()
    if screenshot:
        # Сохраняем временный файл для демонстрации
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        screenshot.save(temp_file.name)
        print(f"   ✅ Шаблон сохранён: {temp_file.name}")

    # Тест 2: поиск объекта (если есть шаблон)
    print("\n2. Поиск объекта на экране...")
    print("   (Пропускаем, так как нужен реальный шаблон)")

    # Тест 3: скриншот экрана
    print("\n3. Делаем скриншот всего экрана...")
    full = finder.capture_fullscreen()
    print(f"   ✅ Скриншот получен, размер: {full.shape if full is not None else 'None'}")

    print("\n✅ Тест завершён")
   