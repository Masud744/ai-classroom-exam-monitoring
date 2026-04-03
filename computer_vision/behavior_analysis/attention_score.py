class AttentionScorer:
    def calculate(self, looking_forward, eyes_closed,
                  talking, phone_detected,
                  face_present, multiple_faces):

        score = 100

        if not face_present:
            score -= 40

        if multiple_faces:
            score -= 30

        if not looking_forward:
            score -= 15

        if eyes_closed:
            score -= 20

        if talking:
            score -= 10

        if phone_detected:
            score -= 30

        if score < 0:
            score = 0

        return score