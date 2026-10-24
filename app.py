from flask import Flask, render_template, request, jsonify
from main import WarmupGenerator
import json
import logging

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Инициализация генератора комплексов
generator = WarmupGenerator('exercises.json')


@app.route('/')
def index():
    """Главная страница с анкетой для спортсмена."""
    return render_template('index.html')


@app.route('/api/generate', methods=['POST'])
def generate_warmup():
    """
    API endpoint для генерации разминочного комплекса.

    Принимает JSON с данными спортсмена:
    {
        "weapon": "foil|sabre|epee",
        "skill_level": "beginner|intermediate|advanced|elite",
        "session_type": "competition|training|recovery",
        "available_time": 5-30,
        "injuries": ["knee_injury", ...],
        "age": опционально,
        "height": опционально,
        "weight": опционально,
        "gender": опционально,
        "training_frequency": "1-2|3-4|5+"  // новое поле
    }

    Возвращает JSON с персонализированным комплексом.
    """
    try:
        # Получаем данные из запроса
        athlete_data = request.json

        if not athlete_data:
            return jsonify({
                "status": "error",
                "message": "Данные спортсмена не предоставлены"
            }), 400

        # Валидация обязательных полей
        required_fields = ['weapon', 'skill_level', 'session_type', 'available_time']
        missing_fields = [field for field in required_fields if field not in athlete_data]

        if missing_fields:
            return jsonify({
                "status": "error",
                "message": f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"
            }), 400

        # Валидация значений
        valid_weapons = ['foil', 'sabre', 'epee']
        valid_levels = ['beginner', 'intermediate', 'advanced', 'elite']
        valid_sessions = ['competition', 'training', 'recovery']

        if athlete_data['weapon'] not in valid_weapons:
            return jsonify({
                "status": "error",
                "message": f"Недопустимый вид оружия. Допустимые: {', '.join(valid_weapons)}"
            }), 400

        if athlete_data['skill_level'] not in valid_levels:
            return jsonify({
                "status": "error",
                "message": f"Недопустимый уровень подготовки. Допустимые: {', '.join(valid_levels)}"
            }), 400

        if athlete_data['session_type'] not in valid_sessions:
            return jsonify({
                "status": "error",
                "message": f"Недопустимый тип сессии. Допустимые: {', '.join(valid_sessions)}"
            }), 400

        available_time = athlete_data.get('available_time', 15)
        if not isinstance(available_time, int) or available_time < 5 or available_time > 30:
            return jsonify({
                "status": "error",
                "message": "Время на разминку должно быть от 5 до 30 минут"
            }), 400

        # Валидация возраста
        age = athlete_data.get('age')
        if age and (age < 8 or age > 70):
            return jsonify({
                "status": "error",
                "message": "Возраст должен быть от 8 до 70 лет"
            }), 400

        # Нормализация данных
        normalized_data = {
            'weapon': athlete_data['weapon'],
            'skill_level': athlete_data['skill_level'],
            'session_type': athlete_data['session_type'],
            'available_time': available_time,
            'injuries': athlete_data.get('injuries', []),
            'age': athlete_data.get('age'),
            'height': athlete_data.get('height'),
            'weight': athlete_data.get('weight'),
            'gender': athlete_data.get('gender'),
            'training_frequency': athlete_data.get('training_frequency', '3-4')
        }

        # Логирование запроса
        logger.info(f"Генерация комплекса для: {normalized_data}")

        # Генерация комплекса
        result = generator.generate_complex(normalized_data)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Ошибка при генерации комплекса: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Внутренняя ошибка сервера: {str(e)}"
        }), 500


@app.route('/api/exercises', methods=['GET'])
def get_exercises():
    """API endpoint для получения списка всех упражнений из базы данных."""
    try:
        with open('exercises.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Ошибка при загрузке упражнений: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Ошибка при загрузке упражнений: {str(e)}"
        }), 500


@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """API endpoint для получения статистики использования системы."""
    try:
        stats = generator.get_usage_statistics()
        return jsonify({
            "status": "success",
            "statistics": stats
        })
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Ошибка при получении статистики: {str(e)}"
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint для мониторинга."""
    return jsonify({
        "status": "healthy",
        "service": "Fencing Warmup Generator",
        "version": "2.0"
    }), 200


@app.errorhandler(404)
def not_found(error):
    """Обработка 404 ошибок."""
    return jsonify({
        "status": "error",
        "message": "Страница не найдена"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Обработка 500 ошибок."""
    return jsonify({
        "status": "error",
        "message": "Внутренняя ошибка сервера"
    }), 500


if __name__ == '__main__':
    # Запуск приложения
    app.run(debug=True, host='0.0.0.0', port=8000)
