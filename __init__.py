# В __init__ приложения сразу задаем источники
base_dir = os.path.dirname(os.path.abspath(__file__))

# Формируем пути ко всем файлам
self.video_path = os.path.join(base_dir, "mouse_v1.webm") [2]
self.reverse_video_path = os.path.join(base_dir, "mouse_v1_reverse.webm")
self.image_path = os.path.join(base_dir, "mouse.png")

# Задаем базовый источник для плеера (без запуска)
self.media_player.setSource(QUrl.fromLocalFile(QFile.encodeName(self.video_path).data().decode('utf-8'))) [2]
