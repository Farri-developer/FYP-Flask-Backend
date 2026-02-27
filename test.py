#
#
# # ---------------- Report By QID (WITH GPT) ----------------
# @report_bp.route("/reportbyqid_with_gpt/<int:qid>", methods=["GET"])
# def question_report_with_gpt(qid):
#     conn = get_db_connection()
#     cursor = conn.cursor()
#
#     query = """
#             SELECT
#                 q.qid,
#                 q.description,
#                 q.duration,
#
#                 COUNT(DISTINCT r.reportid) AS total_attempts,
#
#                 (
#                     SELECT COUNT(*)
#                     FROM QuestionAttempt qa2
#                     WHERE qa2.qid = q.qid
#                       AND qa2.gptindex = 1
#                 ) AS total_attempts_gpt,
#
#                 CONCAT(
#                     CAST(AVG(r.AfterQuestionsys) AS INT),
#                     '/',
#                     CAST(AVG(r.AfterQuestionDIA) AS INT)
#                 ) AS bp,
#
#                 AVG(r.HR)     AS avg_hr,
#                 AVG(r.SDNN)   AS avg_sdnn,
#                 AVG(r.RMSSD)  AS avg_rmssd,
#                 AVG(r.SI)     AS avg_si,
#
#                 (
#                     SELECT TOP 1 r2.stresslevel
#                     FROM Reports r2
#                     WHERE r2.qid = q.qid
#                     GROUP BY r2.stresslevel
#                     ORDER BY COUNT(*) DESC
#                 ) AS most_common_stress_level
#
#             FROM Question q
#
#             LEFT JOIN Reports r
#                 ON q.qid = r.qid
#
#             WHERE q.qid = ?
#
#             GROUP BY
#                 q.qid,
#                 q.description,
#                 q.duration
#         """
#
#     cursor.execute(query, (qid,))
#     row = cursor.fetchone()
#     conn.close()
#
#     if not row:
#         return jsonify({"error": "Question not found"}), 404
#
#     response = {
#         "qid": row[0],
#         "description": row[1],
#         "duration": row[2],
#         "total_attempts": row[3],
#         "total_attempts_gpt": row[4],
#         "avg_bp": row[5],
#         "avg_heart_rate": row[6],
#         "avg_sdnn": row[7],
#         "avg_rmssd": row[8],
#         "avg_si": row[9],
#         "most_common_stress_level": row[10],
#     }
#
#     return jsonify(response), 200
#
#
#
# # ---------------- Report By QID (WITHOUT GPT) ----------------
# @report_bp.route("/reportbyqid_without_gpt/<int:qid>", methods=["GET"])
# def question_report_without_gpt(qid):
#     conn = get_db_connection()
#     cursor = conn.cursor()
#
#     query = """
#                 SELECT
#                     q.qid,
#                     q.description,
#                     q.duration,
#
#                     COUNT(DISTINCT r.reportid) AS total_attempts,
#
#                     (
#                         SELECT COUNT(*)
#                         FROM QuestionAttempt qa2
#                         WHERE qa2.qid = q.qid
#                           AND qa2.gptindex = 1
#                     ) AS total_attempts_gpt,
#
#                     CONCAT(
#                         CAST(AVG(r.AfterQuestionsys) AS INT),
#                         '/',
#                         CAST(AVG(r.AfterQuestionDIA) AS INT)
#                     ) AS bp,
#
#                     AVG(r.HR)     AS avg_hr,
#                     AVG(r.SDNN)   AS avg_sdnn,
#                     AVG(r.RMSSD)  AS avg_rmssd,
#                     AVG(r.SI)     AS avg_si,
#
#                     (
#                         SELECT TOP 1 r2.stresslevel
#                         FROM Reports r2
#                         WHERE r2.qid = q.qid
#                         GROUP BY r2.stresslevel
#                         ORDER BY COUNT(*) DESC
#                     ) AS most_common_stress_level
#
#                 FROM Question q
#
#                 LEFT JOIN Reports r
#                     ON q.qid = r.qid
#
#                 WHERE q.qid = ?
#
#                 GROUP BY
#                     q.qid,
#                     q.description,
#                     q.duration
#             """
#
#     cursor.execute(query, (qid,))
#     row = cursor.fetchone()
#     conn.close()
#
#     if not row:
#         return jsonify({"error": "Question not found"}), 404
#
#     response = {
#         "qid": row[0],
#         "description": row[1],
#         "duration": row[2],
#         "total_attempts": row[3],
#         "total_attempts_gpt": row[4],
#         "avg_bp": row[5],
#         "avg_heart_rate": row[6],
#         "avg_sdnn": row[7],
#         "avg_rmssd": row[8],
#         "avg_si": row[9],
#         "most_common_stress_level": row[10],
#     }
#
#     return jsonify(response), 200
