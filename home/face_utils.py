import os
import cv2
import numpy as np
from insightface.app import FaceAnalysis
from django.conf import settings
from home.models import Student, FaceEmbedding

# Initialize once globally
face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
face_app.prepare(ctx_id=0)

def train_face_database():
    KNOWN_FOLDER = os.path.join(settings.BASE_DIR, 'home', 'known_faces')
    added, skipped_files = 0, []

    for root, _, files in os.walk(KNOWN_FOLDER):
        roll_number = os.path.basename(root)
        if not roll_number or roll_number.lower() == "known_faces":
            continue

        try:
            student = Student.objects.get(roll_number=roll_number)
        except Student.DoesNotExist:
            print(f"❌ No student with roll number: {roll_number}")
            continue

        for file in files:
            if not file.lower().endswith((".jpg", ".jpeg", ".png")):
                continue

            file_path = os.path.join(root, file)
            img = cv2.imread(file_path)
            if img is None:
                print(f"❌ Could not read image: {file_path}")
                skipped_files.append(file_path)
                continue

            img_resized = cv2.resize(img, (640, 640))
            faces = face_app.get(img_resized)

            if not faces:
                print(f"🚫 No face in {file_path}")
                skipped_files.append(file_path)
                continue

            embedding = faces[0].embedding
            norm = np.linalg.norm(embedding)
            if norm == 0:
                print(f"🚫 Invalid embedding for {file_path}")
                skipped_files.append(file_path)
                continue

            embedding = (embedding / norm).astype(np.float32)
            FaceEmbedding.objects.create(
                student=student,
                embedding=embedding.tobytes(),
                image_name=file
            )
            print(f"✅ Embedded {roll_number} from {file}")
            added += 1

    return {
        "added": added,
        "skipped": skipped_files,
        "total_images": added + len(skipped_files)
    }
