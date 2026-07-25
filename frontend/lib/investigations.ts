export type InvestigationStatus = "open" | "in_review" | "validated" | "archived";
export type EvidenceType = "primary" | "secondary" | "dataset" | "expert" | "other";
export type EvidenceRelationship = "supports" | "contradicts" | "neutral";
export type AssessmentLevel = "low" | "medium" | "high";
export type ValidationStatus = "unreviewed" | "supported" | "mixed" | "contradicted" | "insufficient";
export type QualityAssessmentStatus = "missing" | "partial" | "complete";

export type Investigation = { id: number; title: string; research_question: string; status: InvestigationStatus; created_at: string; updated_at: string };
export type InvestigationClaim = { id: number; investigation_id: number; statement: string; confidence_level: AssessmentLevel | null; confidence_rationale: string | null; created_at: string; updated_at: string };
export type ClaimEvidence = { id: number; claim_id: number; source_title: string; source_url: string; evidence_type: EvidenceType; relationship: EvidenceRelationship; notes: string | null; credibility_rating: AssessmentLevel | null; credibility_rationale: string | null; created_at: string; updated_at: string };
export type ClaimValidationJudgment = { id: number; claim_id: number; reviewer_id: number; validation_status: ValidationStatus; confidence_level: AssessmentLevel; rationale: string; unresolved_questions: string | null; reviewed_at: string; is_stale: boolean };
export type ClaimValidationJudgmentCreate = { validation_status: ValidationStatus; confidence_level: AssessmentLevel; rationale: string; unresolved_questions?: string | null };
export type ClaimValidationSummary = { claim_id: number; confidence_level: AssessmentLevel | null; supporting_count: number; contradicting_count: number; neutral_count: number; assessed_evidence_count: number; total_evidence_count: number; has_unresolved_contradiction: boolean };
export type InvestigationValidationSummary = { investigation_id: number; claim_count: number; assessed_claim_count: number; low_confidence_count: number; medium_confidence_count: number; high_confidence_count: number; unresolved_contradiction_count: number; claims: ClaimValidationSummary[] };

export type ValidationMapEvidenceLink = { evidence_id: number; source_title: string; source_url: string; evidence_type: string; relationship: "supporting" | "contradicting" | "contextual"; stored_relationship: EvidenceRelationship; classification_rule: string; credibility_rating: string | null; credibility_rationale: string | null; notes: string | null };
export type ValidationMapHumanReview = { status: "not_reviewed" | "current" | "stale"; validation_status: string | null; confidence_level: string | null; rationale: string | null; unresolved_questions: string | null; reviewed_at: string | null; authorship: "user_judgment" };
export type ValidationMapClaim = { claim_id: number; sequence: number; statement: string; status: "supported" | "contested" | "insufficient" | "unreviewed"; status_rule: string; relationship_counts: Record<string, number>; confidence_inputs: string[]; evidence_links: ValidationMapEvidenceLink[]; missing_evidence_requirements: string[]; unresolved_gaps: string[]; human_review: ValidationMapHumanReview };
export type ClaimEvidenceValidationMap = { contract_version: string; investigation_id: number; title: string; status: "active" | "empty"; claims: ValidationMapClaim[]; summary_counts: Record<string, number>; unresolved_gaps: string[]; generated_from: "stored_evidence_rules"; generated_from_stored_state_at: string; interpretation_notice: string };

export type EvidenceGapSourceRequirement = { requirement: string; source_constraints: string[]; derived_from: "recorded_gap" };
export type EvidenceGapRemediationAction = { claim_id: number; claim_sequence: number; statement: string; claim_status: "supported" | "contested" | "insufficient" | "unreviewed"; priority: number; priority_rule: string; action_type: "resolve_contradiction" | "collect_direct_evidence" | "attach_initial_evidence" | "refresh_human_review"; rationale: string; source_requirements: EvidenceGapSourceRequirement[]; review_refresh_required: boolean; completion_criteria: string[]; stored_inputs: string[] };
export type EvidenceGapRemediationPlan = { contract_version: string; investigation_id: number; title: string; status: "action_required" | "complete" | "empty"; actions: EvidenceGapRemediationAction[]; action_counts: Record<string, number>; generated_from: "validation_map_stored_inputs"; generated_from_stored_state_at: string; interpretation_notice: string };

export type RemediationProgressStatus = "not_started" | "in_progress" | "blocked" | "ready_for_review" | "dismissed";
export type RemediationCurrentAction = { action_type: EvidenceGapRemediationAction["action_type"]; priority: number; rationale: string; completion_criteria: string[]; generated_from_stored_state_at: string };
export type RemediationProgressEntry = { claim_id: number; claim_sequence: number | null; statement: string; status: RemediationProgressStatus; notes: string | null; authorship: "user_authored"; is_stale: boolean; stale_reasons: string[]; action_type_snapshot: EvidenceGapRemediationAction["action_type"]; priority_snapshot: number; plan_generated_at_snapshot: string; current_action: RemediationCurrentAction | null; created_at: string; updated_at: string };
export type RemediationProgressLedger = { contract_version: string; investigation_id: number; title: string; status: "empty" | "active"; entries: RemediationProgressEntry[]; generated_from: "user_progress_and_current_remediation_plan"; interpretation_notice: string };
export type RemediationProgressHistoryEvent = { event_id: number; claim_id: number; status: RemediationProgressStatus; notes: string | null; authorship: "user_authored"; action_type_snapshot: EvidenceGapRemediationAction["action_type"]; priority_snapshot: number; plan_generated_at_snapshot: string; recorded_at: string };
export type RemediationProgressHistory = { contract_version: string; investigation_id: number; claim_id: number; status: "empty" | "active"; events: RemediationProgressHistoryEvent[]; generated_from: "append_only_user_progress_history"; interpretation_notice: string };

export type InvestigationProvenanceCategory = "claim" | "evidence" | "validation" | "remediation_progress" | "remediation_history";
export type InvestigationProvenanceEvent = { event_key: string; category: InvestigationProvenanceCategory; action: "created" | "updated" | "reviewed" | "recorded"; entity_type: string; entity_id: number; claim_id: number | null; claim_statement: string | null; authorship: "user_authored" | "human_judgment"; summary: string; occurred_at: string; source_table: string; source_record_id: number };
export type InvestigationProvenanceTimeline = { contract_version: string; investigation_id: number; title: string; status: "empty" | "active"; events: InvestigationProvenanceEvent[]; generated_from: "stored_investigation_records"; interpretation_notice: string };

export type ReviewQueueReason = "stale_validation" | "missing_validation" | "unresolved_contradiction" | "blocked_remediation" | "remediation_ready_for_review";
export type ReviewQueueItem = { item_key: string; investigation_id: number; investigation_title: string; investigation_status: InvestigationStatus; claim_id: number; claim_statement: string; reason_type: ReviewQueueReason; workflow_priority: number; reason: string; stored_inputs: string[]; latest_relevant_at: string; source_tables: string[]; source_record_ids: number[] };
export type CrossInvestigationReviewQueue = { contract_version: string; status: "empty" | "active"; item_count: number; items: ReviewQueueItem[]; generated_from: "stored_owner_investigation_records"; interpretation_notice: string };

export type ResearchLearningRecommendation = { competency: string; lesson_slug: string; lesson_title: string; gap_type: string; priority: number; reason: string };
export type InvestigationEducationRecommendations = { investigation_id: number; recommendation_count: number; completion_authority: "adaptive_assessment_only"; recommendations: ResearchLearningRecommendation[] };
export type QualityAssessmentDimension = { key: string; label: string; status: QualityAssessmentStatus; counts: Record<string, number>; explanation: string };
export type InvestigationQualityAssessment = { contract_version: string; investigation_id: number; dimensions: QualityAssessmentDimension[]; recommendations: string[]; generated_from_stored_state_at: string; interpretation_notice: string };
export type InvestigationCreate = { title: string; research_question: string };
export type InvestigationUpdate = Partial<InvestigationCreate> & { status?: InvestigationStatus };
