package org.example.server_job.student.service;

import java.util.List;
import java.util.Map;

public interface StudentPortalActivityService {

    Map<String, Object> getReviewTags();

    Map<String, Object> getMeSummary(String studentId);

    Map<String, Object> getMeContext(String studentId, String jobId, String creditCode);

    Map<String, Object> getMeFavorites(String studentId);

    Map<String, Object> toggleFavorite(String studentId, String jobId);

    Map<String, Object> getMeFollows(String studentId);

    Map<String, Object> toggleFollow(String studentId, String creditCode);

    Map<String, Object> listMyJobReviewsEnriched(String studentId);

    Map<String, Object> listMyCompanyReviewsEnriched(String studentId);

    Map<String, Object> upsertJobReview(String studentId, String jobId, int stars, String comment, List<String> tags);

    Map<String, Object> upsertCompanyReview(String studentId, String creditCode, int stars, String comment, List<String> tags);

    Map<String, Object> deleteJobReview(String studentId, String jobId);

    Map<String, Object> deleteCompanyReview(String studentId, String creditCode);

    Map<String, Object> aggregateJobReviews(String jobId);

    Map<String, Object> aggregateCompanyReviews(String creditCode);
}
