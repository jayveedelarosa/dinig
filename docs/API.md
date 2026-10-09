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
| `/readings` | POST | Read and Check: convert, score, save, delete audio, save rule-based tip | form `pupil_id, story_id, seconds_taken, audio` | `{reading_id, words:[{word, status}], words_correct, total_words, seconds_taken}` |
| `/quiz/{reading_id}` | GET | 2 questions. **Now:** the story's backup questions (`source: "backup"`). Next: Qwen with 8 s fallback | none | `{source, questions:[{question_id, question}]}` |
| `/quiz/answer` | POST | Judge a spoken answer. **Now:** keyword match with the backup answer; no `question_id` = `unchecked`. Saves only the result | form `reading_id, question, question_id?, audio` | `{result: right/wrong/unchecked, message}` |
| `/practice` | POST | Practice sentences for up to 3 red words. **Now:** template "I can read the word ___." | JSON `{reading_id}` | `{practice_id, sentences, target_words, wrong_before}` |
| `/practice/{id}/check` | POST | Score the practice reading; target words not read green are still missed | form `audio` | `{words, wrong_before, wrong_after, still_missed}` |
| `/teacher/class` | GET | Class View data for every pupil (nulls if no readings yet). Trouble words = red words of the last 5 readings + still_missed, top 5 | none | `[{id, first_name, class_no, grade, latest_accuracy, latest_words_correct, latest_total_words, latest_seconds, trouble_words, tip, last5, last_read_at}]` |

`status` is `green` (correct), `red` (wrong) or `grey` (skipped).
