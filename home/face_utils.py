import os
import cv2
import numpy as np
import warnings
from .models import Student, FaceEmbedding
from insightface.app import FaceAnalysis
from django.conf import settings

warnings.filterwarnings("ignore", category=FutureWarning)

# Initialize face detection and embedding model
face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
face_app.prepare(ctx_id=0)

def train_face_database():
    KNOWN_FOLDER = os.path.join(settings.BASE_DIR, 'home', 'known_faces')
    added = 0
    skipped_files = []
    total_images = 0

    for root, _, files in os.walk(KNOWN_FOLDER):
        roll_number = os.path.basename(root)

        if not roll_number or roll_number == 'known_faces':
            continue

        try:
            student = Student.objects.get(roll_number=roll_number)
        except Student.DoesNotExist:
            print(f"❌ Student {roll_number} not found in DB")
            continue

        for file in files:
            if not file.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue

            file_path = os.path.join(root, file)
            img = cv2.imread(file_path)

            if img is None:
                print(f"❌ Failed to read {file_path}")
                skipped_files.append(file_path)
                continue

            img_resized = cv2.resize(img, (640, 640))
            faces = face_app.get(img_resized)

            if faces:
                face = faces[0]
                embedding = face.embedding.astype(np.float32).tobytes()

                FaceEmbedding.objects.create(
                    student=student,
                    embedding=embedding,
                    image_name=file
                )

                print(f"✅ Saved embedding for {roll_number} from image {file}")
                added += 1
                total_images += 1
            else:
                print(f"🚫 No face found in {file_path}")
                skipped_files.append(file_path)

    print(f"🧠 Total embeddings stored: {added}")
    return {
        "added": added,
        "skipped": skipped_files,
        "total_images": total_images
    }
