class SuspiciousScorer:
    def calculate(self, looking_forward, eyes_closed,
                  talking, phone_detected,
                  face_present, multiple_faces):
        score = 0
        if phone_detected:
            score += 40
        if multiple_faces:
            score += 30
        if not face_present:
            score += 20
        if not looking_forward:
            score += 15
        if talking:
            score += 20
        if eyes_closed:
            score += 10
        if score > 100:
            score = 100
        return score