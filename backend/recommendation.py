"""Conservative educational pattern matching; not a diagnosis or prescription."""
EMERGENCY_SYMPTOMS = {"chest pain", "difficulty breathing", "shortness of breath", "fainting", "confusion", "seizure", "severe bleeding", "face drooping", "slurred speech"}
PATTERNS = [
    ({"fever", "headache", "body pain", "cough"}, "Flu-like illness"),
    ({"sneezing", "runny nose", "itchy eyes"}, "Seasonal allergy pattern"),
    ({"headache", "nausea", "light sensitivity"}, "Headache / migraine-like pattern"),
    ({"sore throat", "cough", "fever"}, "Upper respiratory symptom pattern"),
    ({"stomach pain", "diarrhea", "nausea"}, "Gastrointestinal symptom pattern"),
]
def assess(data: dict) -> dict:
    symptoms = {value.strip().lower() for value in data["symptoms"]}
    urgent = sorted(symptoms & EMERGENCY_SYMPTOMS)
    if urgent:
        return {"prediction":"Urgent evaluation needed","confidence":100,"emergency":True,"emergency_message":"These symptoms can be serious. Contact local emergency services or seek urgent in-person care now.","matched_symptoms":urgent,"medicine_guidance":[],"home_care":["Do not delay emergency evaluation.","If safe, have someone stay with you."],"diet":[],"exercise":[],"specialist":"Emergency department / emergency services"}
    best_score, prediction, matched = 0, "Non-specific symptom pattern", []
    for features, label in PATTERNS:
        overlap = sorted(features & symptoms)
        if len(overlap) > best_score: best_score, prediction, matched = len(overlap), label, overlap
    return {"prediction":prediction,"confidence":min(88,42+best_score*15),"emergency":False,"emergency_message":None,"matched_symptoms":matched,"medicine_guidance":["Ask a pharmacist or licensed clinician about symptom relief that is safe for you.","Do not start medication without checking allergies, existing conditions, and interactions."],"home_care":["Rest and keep hydrated.","Track symptoms, temperature, and when they began.","Seek care if symptoms worsen or persist."],"diet":["Choose regular, balanced meals and fluids.","Prefer light foods if you feel nauseated."],"exercise":["Avoid strenuous exercise while unwell.","Resume gentle activity only when you feel better."],"specialist":"Primary care / general physician if symptoms persist, worsen, or concern you"}
