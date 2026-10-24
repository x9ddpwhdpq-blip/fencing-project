import json
import time
from typing import List, Dict, Any, Tuple
from datetime import datetime


class WarmupGenerator:
    """Класс для генерации индивидуальных разминочных комплексов для фехтовальщиков."""

    def __init__(self, exercises_file: str = 'exercises.json'):
        """Инициализация генератора."""
        self.exercises = self._load_exercises(exercises_file)
        self.usage_stats = {
            'total_generations': 0,
            'last_generation': None,
            'weapon_stats': {'foil': 0, 'sabre': 0, 'epee': 0},
            'level_stats': {'beginner': 0, 'intermediate': 0, 'advanced': 0, 'elite': 0}
        }

    def _load_exercises(self, file_path: str) -> List[Dict[str, Any]]:
        """Загрузка базы данных упражнений из JSON файла."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('exercises', [])
        except FileNotFoundError:
            raise FileNotFoundError(f"Файл {file_path} не найден!")
        except json.JSONDecodeError:
            raise ValueError(f"Ошибка при чтении JSON файла {file_path}")

    def update_statistics(self, athlete_profile: Dict[str, Any]):
        """Обновление статистики использования."""
        self.usage_stats['total_generations'] += 1
        self.usage_stats['last_generation'] = datetime.now().isoformat()

        weapon = athlete_profile.get('weapon')
        if weapon in self.usage_stats['weapon_stats']:
            self.usage_stats['weapon_stats'][weapon] += 1

        level = athlete_profile.get('skill_level')
        if level in self.usage_stats['level_stats']:
            self.usage_stats['level_stats'][level] += 1

    def get_usage_statistics(self) -> Dict[str, Any]:
        """Получение статистики использования системы."""
        return self.usage_stats

    def filter_exercises(self, athlete_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Многоуровневая фильтрация упражнений на основе профиля спортсмена."""
        filtered = []
        injuries = athlete_profile.get('injuries', [])
        skill_level = athlete_profile.get('skill_level', '')
        session_type = athlete_profile.get('session_type', '')
        weapon = athlete_profile.get('weapon', '')
        age = athlete_profile.get('age')

        for exercise in self.exercises:
            # ЭТАП 1: Фильтр по противопоказаниям (ЖЕСТКИЙ)
            contraindications = exercise.get('contraindications', [])
            if any(injury in contraindications for injury in injuries):
                continue

            # ЭТАП 2: Фильтр по уровню подготовки (ЖЕСТКИЙ)
            exercise_skill_levels = exercise.get('skill_level', [])
            if skill_level not in exercise_skill_levels:
                continue

            # ЭТАП 3: Фильтр по возрасту (для некоторых упражнений)
            if age and age < 16 and exercise.get('intensity') == 'high':
                # Для спортсменов младше 16 ограничиваем высокоинтенсивные упражнения
                if exercise.get('category') in ['power', 'cardio']:
                    continue

            # ЭТАП 4: Фильтр по виду оружия для специфических упражнений
            if exercise.get('weapon_specific', False):
                suitable_for = exercise.get('suitable_for', [])
                if weapon not in suitable_for:
                    continue

            # ЭТАП 5: Фильтр по типу сессии
            if session_type == 'recovery':
                # Восстановительная тренировка - только низкая/средняя интенсивность
                if exercise.get('intensity') == 'high':
                    continue
                # Приоритет упражнениям на восстановление и гибкость
                if exercise.get('category') in ['recovery', 'flexibility', 'joint_mobility']:
                    pass
            elif session_type == 'competition':
                # Соревновательная разминка - больше специальных упражнений
                if exercise.get('category') == 'special':
                    pass

            filtered.append(exercise)

        return filtered

    def calculate_effectiveness(self, exercise: Dict[str, Any],
                                athlete_profile: Dict[str, Any]) -> float:
        """Расчет итогового балла эффективности упражнения для конкретного спортсмена."""

        # Базовая эффективность из эксперимента
        base_score = exercise.get('effectiveness_score', 0.0)

        # Расчет комбинированного балла на основе показателей оксигенации и пульса
        spO2_change = abs(exercise.get('spO2_change', 0.0))
        hr_increase = exercise.get('hr_increase', 0)

        # Балл оксигенации: чем меньше падение SpO2, тем выше балл
        spO2_score = max(0, 10 - (spO2_change * 2))

        # Балл пульса: чем больше рост пульса, тем выше балл (но с ограничением)
        hr_score = min(10, hr_increase / 6.0)

        # Комбинированный балл (60% оксигенация, 40% пульс)
        combined_score = (spO2_score * 0.6) + (hr_score * 0.4)

        # БОНУСЫ
        bonuses = 0.0

        # Бонус за соответствие виду оружия
        weapon = athlete_profile.get('weapon', '')
        suitable_weapons = exercise.get('suitable_for', [])
        if weapon in suitable_weapons:
            bonuses += 1.0

        # Бонус за соответствие типу сессии
        session_type = athlete_profile.get('session_type', '')
        session_suitable = exercise.get('session_type_suitable', [])
        if session_type in session_suitable:
            bonuses += 0.5

        # Бонус за высокий приоритет
        priority = exercise.get('priority', 5)
        if priority == 1:
            bonuses += 0.5
        elif priority == 2:
            bonuses += 0.3

        # Бонус за соответствие интенсивности типу сессии
        intensity = exercise.get('intensity', 'medium')
        if session_type == 'competition' and intensity == 'high':
            bonuses += 0.3
        elif session_type == 'recovery' and intensity == 'low':
            bonuses += 0.3

        # Бонус за возрастную адекватность
        age = athlete_profile.get('age')
        if age:
            if age < 16 and intensity == 'medium':
                bonuses += 0.2
            elif age > 40 and intensity == 'low':
                bonuses += 0.2

        # ШТРАФЫ
        penalties = 0.0

        # Штраф за несоответствие виду оружия для специфических упражнений
        if exercise.get('weapon_specific', False) and weapon not in suitable_weapons:
            penalties += 1.0

        # Штраф за несоответствие типу сессии
        if session_type not in session_suitable:
            penalties += 0.5

        # Штраф за низкий приоритет
        if priority >= 4:
            penalties += 0.3

        # Штраф за высокую интенсивность при травмах
        injuries = athlete_profile.get('injuries', [])
        if injuries and intensity == 'high':
            penalties += 0.5

        # Итоговый балл
        final_score = base_score + combined_score + bonuses - penalties

        return round(final_score, 2)

    def rank_exercises(self, filtered_exercises: List[Dict[str, Any]],
                       athlete_profile: Dict[str, Any]) -> List[Tuple[Dict[str, Any], float]]:
        """Ранжирование отфильтрованных упражнений по эффективности."""
        ranked = []

        for exercise in filtered_exercises:
            effectiveness = self.calculate_effectiveness(exercise, athlete_profile)
            ranked.append((exercise, effectiveness))

        # Сортировка по убыванию балла эффективности
        ranked.sort(key=lambda x: x[1], reverse=True)

        return ranked

    def generate_complex(self, athlete_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация персонализированного разминочного комплекса."""

        # Обновляем статистику
        self.update_statistics(athlete_profile)

        # Шаг 1: Фильтрация
        filtered = self.filter_exercises(athlete_profile)

        # Обработка граничного случая: нет подходящих упражнений
        if not filtered:
            return self._generate_fallback_complex(athlete_profile)

        # Шаг 2: Ранжирование
        ranked = self.rank_exercises(filtered, athlete_profile)

        # Шаг 3: Подбор упражнений
        available_time = athlete_profile.get('available_time', 15)
        selected_exercises = []
        used_time = 0
        categories_included = set()

        # Обязательные категории для разминки фехтовальщика
        mandatory_categories = ['joint_mobility', 'cardio', 'special']

        for exercise, score in ranked:
            duration = exercise.get('duration', 0)

            # Проверяем, помещается ли упражнение во время
            if used_time + duration <= available_time:
                selected_exercises.append({
                    'exercise': exercise,
                    'effectiveness_score': score,
                    'reason': self._get_selection_reason(exercise, athlete_profile)
                })
                used_time += duration
                categories_included.add(exercise.get('category', ''))

            # Если осталось меньше 2 минут, прекращаем подбор
            if available_time - used_time < 2:
                break

        # Шаг 4: Балансировка по категориям
        selected_exercises = self._balance_categories(
            selected_exercises, ranked, available_time, used_time, mandatory_categories
        )

        # Шаг 5: Оптимизация последовательности
        selected_exercises = self._optimize_sequence(selected_exercises)

        # Формирование результата
        return self._format_result(selected_exercises, athlete_profile, used_time)

    def _balance_categories(self, selected: List[Dict], ranked: List[Tuple],
                            available_time: int, used_time: int,
                            mandatory_categories: List[str]) -> List[Dict]:
        """Балансировка комплекса по категориям упражнений."""

        selected_categories = {ex['exercise'].get('category') for ex in selected}

        # Проверяем наличие обязательных категорий
        missing_categories = [cat for cat in mandatory_categories if cat not in selected_categories]

        # Добавляем упражнения из недостающих категорий
        for category in missing_categories:
            for exercise, score in ranked:
                if exercise.get('category') == category:
                    duration = exercise.get('duration', 0)

                    # Проверяем, не добавлено ли уже это упражнение
                    if any(ex['exercise']['id'] == exercise['id'] for ex in selected):
                        continue

                    # Если помещается во время, добавляем
                    if used_time + duration <= available_time:
                        selected.append({
                            'exercise': exercise,
                            'effectiveness_score': score,
                            'reason': f'Добавлено для балансировки категории "{category}"'
                        })
                        used_time += duration
                        break

        return selected

    def _optimize_sequence(self, selected: List[Dict]) -> List[Dict]:
        """Оптимизация последовательности упражнений для разминки фехтовальщика."""

        # Порядок категорий для оптимальной разминки
        category_order = {
            'joint_mobility': 1,
            'recovery': 2,
            'cardio': 3,
            'special': 4,
            'power': 5,
            'flexibility': 6
        }

        # Сортируем по категориям и интенсивности
        selected.sort(key=lambda x: (
            category_order.get(x['exercise'].get('category', ''), 7),
            x['exercise'].get('priority', 5)
        ))

        return selected

    def _get_selection_reason(self, exercise: Dict, athlete_profile: Dict) -> str:
        """Генерация объяснения, почему выбрано это упражнение."""
        reasons = []

        # Причины на основе эффективности
        if exercise.get('effectiveness_score', 0) >= 9.0:
            reasons.append("высокая эффективность")
        elif exercise.get('effectiveness_score', 0) <= 6.0:
            reasons.append("базовое упражнение")

        # Причины на основе категории
        category = exercise.get('category', '')
        if category == 'joint_mobility':
            reasons.append("подготовка суставов")
        elif category == 'special':
            reasons.append("специальная подготовка")
        elif category == 'cardio':
            reasons.append("активация ССС")

        # Причины на основе профиля
        session_type = athlete_profile.get('session_type', '')
        if session_type == 'competition' and exercise.get('intensity') == 'high':
            reasons.append("подготовка к старту")
        elif session_type == 'recovery' and exercise.get('intensity') == 'low':
            reasons.append("восстановительный эффект")

        if not reasons:
            reasons.append("включено в комплекс")

        return ", ".join(reasons)

    def _format_result(self, selected_exercises: List[Dict],
                       athlete_profile: Dict, total_duration: int) -> Dict[str, Any]:
        """Форматирование результата для отправки клиенту."""

        exercises_list = []
        categories = set()
        total_effectiveness = 0.0

        for item in selected_exercises:
            exercise = item['exercise']
            exercises_list.append({
                'id': exercise.get('id'),
                'name': exercise.get('name'),
                'duration': exercise.get('duration'),
                'description': exercise.get('description'),
                'technique': exercise.get('technique'),
                'category': exercise.get('category'),
                'subcategory': exercise.get('subcategory'),
                'target_muscles': exercise.get('target_muscles', []),
                'breathing_technique': exercise.get('breathing_technique', 'Не указана'),
                'effectiveness_score': item['effectiveness_score'],
                'reason_selected': item['reason']
            })
            categories.add(exercise.get('category', ''))
            total_effectiveness += item['effectiveness_score']

        avg_effectiveness = total_effectiveness / len(exercises_list) if exercises_list else 0.0

        # Генерация рекомендаций
        recommendations = self._generate_recommendations(athlete_profile, selected_exercises)

        # Генерация предупреждений
        warnings = self._generate_warnings(athlete_profile, selected_exercises)

        return {
            'status': 'success',
            'generated_at': datetime.now().isoformat(),
            'athlete_profile': athlete_profile,
            'warmup_complex': {
                'total_duration': total_duration,
                'exercises': exercises_list,
                'statistics': {
                    'total_exercises': len(exercises_list),
                    'avg_effectiveness': round(avg_effectiveness, 2),
                    'categories_included': list(categories)
                },
                'recommendations': recommendations,
                'warnings': warnings
            }
        }

    def _generate_recommendations(self, athlete_profile: Dict,
                                  exercises: List[Dict]) -> List[str]:
        """Генерация персональных рекомендаций для спортсмена."""

        recommendations = [
            "Выполняйте упражнения в указанной последовательности",
            "Следите за техникой выполнения каждого упражнения",
            "Контролируйте пульс во время разминки (целевая зона: 120-150 уд/мин)"
        ]

        # Рекомендации на основе профиля
        injuries = athlete_profile.get('injuries', [])
        if injuries:
            recommendations.append(
                "⚠️ При возникновении боли или дискомфорта прекратите упражнение"
            )

        session_type = athlete_profile.get('session_type', '')
        if session_type == 'competition':
            recommendations.append(
                "Этот комплекс подготовит вас к соревновательной нагрузке. Выполняйте за 15-20 минут до старта"
            )
            recommendations.append(
                "После разминки сохраняйте тепло в мышцах - используйте разминочный костюм"
            )
        elif session_type == 'recovery':
            recommendations.append(
                "Комплекс направлен на восстановление. Избегайте перегрузок и прислушивайтесь к своему телу"
            )

        skill_level = athlete_profile.get('skill_level', '')
        if skill_level == 'beginner':
            recommendations.append(
                "Если какое-то упражнение вызывает затруднения, уменьшите интенсивность или пропустите его"
            )
        elif skill_level == 'elite':
            recommendations.append(
                "Можете увеличить интенсивность упражнений на 10-15% при хорошем самочувствии"
            )

        # Рекомендации на основе упражнений
        special_exercises = [ex for ex in exercises if ex['exercise'].get('category') == 'special']
        if len(special_exercises) < 2:
            recommendations.append(
                "Рекомендуется добавить больше специальных упражнений с оружием в следующую разминку"
            )

        return recommendations

    def _generate_warnings(self, athlete_profile: Dict,
                           exercises: List[Dict]) -> List[str]:
        """Генерация предупреждений для спортсмена."""

        warnings = []

        # Предупреждения на основе травм
        injuries = athlete_profile.get('injuries', [])
        if 'knee_injury' in injuries:
            warnings.append(
                "⚠️ Осторожно при выполнении упражнений с нагрузкой на колени"
            )
        if 'shoulder_injury' in injuries:
            warnings.append(
                "⚠️ Ограничьте амплитуду движений в плечевых суставах"
            )

        # Предупреждения на основе возраста
        age = athlete_profile.get('age')
        if age and age < 14:
            warnings.append(
                "⚠️ Для юных спортсменов ограничена интенсивность. Следите за самочувствием"
            )
        elif age and age > 50:
            warnings.append(
                "⚠️ Увеличьте время разминки и уменьшите интенсивность прыжковых упражнений"
            )

        # Предупреждения на основе упражнений
        high_intensity_exercises = [ex for ex in exercises
                                    if ex['exercise'].get('intensity') == 'high']
        if len(high_intensity_exercises) > 2:
            warnings.append(
                "⚠️ Комплекс содержит несколько высокоинтенсивных упражнений. Следите за восстановлением"
            )

        return warnings

    def _generate_fallback_complex(self, athlete_profile: Dict) -> Dict[str, Any]:
        """Генерация базового комплекса, если нет подходящих упражнений."""

        # Универсальные упражнения без противопоказаний
        universal_exercises = [
            ex for ex in self.exercises
            if not ex.get('contraindications') and
               'beginner' in ex.get('skill_level', []) and
               ex.get('intensity') in ['low', 'medium']
        ]

        if not universal_exercises:
            return {
                'status': 'warning',
                'message': 'Не удалось подобрать подходящий комплекс',
                'athlete_profile': athlete_profile,
                'warmup_complex': {
                    'total_duration': 0,
                    'exercises': [],
                    'statistics': {
                        'total_exercises': 0,
                        'avg_effectiveness': 0.0,
                        'categories_included': []
                    },
                    'recommendations': [
                        "⚠️ Не удалось подобрать подходящий комплекс на основе ваших данных.",
                        "Рекомендуется консультация с тренером для составления индивидуальной разминки."
                    ],
                    'warnings': [
                        "Обратитесь к тренеру или врачу для корректировки ограничений"
                    ]
                }
            }

        # Формируем базовый комплекс
        available_time = athlete_profile.get('available_time', 15)
        selected = []
        used_time = 0

        # Обязательные базовые упражнения
        basic_exercises = [
            ex for ex in universal_exercises
            if ex.get('category') in ['joint_mobility', 'cardio']
        ]

        for exercise in basic_exercises[:3]:
            duration = exercise.get('duration', 0)
            if used_time + duration <= available_time:
                selected.append({
                    'exercise': exercise,
                    'effectiveness_score': exercise.get('effectiveness_score', 5.0),
                    'reason': 'Базовое универсальное упражнение'
                })
                used_time += duration

        return self._format_result(selected, athlete_profile, used_time)
