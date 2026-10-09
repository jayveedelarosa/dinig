# API

All routes run on http://localhost:8000 (bound to 127.0.0.1). No route calls the internet.
Audio uploads are form-data with a `.webm` file in `audio`; the server deletes audio right after scoring.

| Route | Method | What it does | Request | Response |
| --- | --- | --- | --- | --- |
| `/health` | GET | Are the local parts ready? | none | `{whisper_loaded, ollama_ready, ollama_model, ffmpeg_found, db_ok}` |
| `/pupils` | GET | List pupils | none | `[{id, first_name, class_no, grade}]` |
| `/pupils` | POST | Add a pupil | JSON `{first_name, class_no?, grade}` | the new pupil (201) |
| `/stories` | GET | List stories | none | `[{id, title, language, grade_level}]` |
| `/stories/{id}` | GET | One story's text (placeholder marker removed) | none | `{id, title, full_text, placeholder}` |
| `/readings` | POST | Read and Check: convert, score, save, delete audio, save rule-based tip | form `pupil_id, story_id, seconds_taken, audio` | `{reading_id, words:[{word, status}], words_correct, total_words, seconds_taken}` (Step 2) |
| `/quiz/{reading_id}` | GET | 2 questions (backup questions for now) | none | `{source, questions:[{question_id, question}]}` (Step 3) |
| `/quiz/answer` | POST | Judge a spoken answer (keyword match for now) | form `reading_id, question, question_id?, audio` | `{result: right/wrong/unchecked, message}` (Step 3) |
| `/practice` | POST | Practice sentences (templates for now) | JSON `{reading_id}` | `{practice_id, sentences, target_words, wrong_before}` (Step 3) |
| `/practice/{id}/check` | POST | Score the practice reading | form `audio` | `{words, wrong_before, wrong_after, still_missed}` (Step 3) |
| `/teacher/class` | GET | Class View data | none | `[{id, first_name, latest_accuracy, latest_seconds, trouble_words, tip, last5, last_read_at}]` (Step 3) |

`status` is `green` (correct), `red` (wrong) or `grey` (skipped).
