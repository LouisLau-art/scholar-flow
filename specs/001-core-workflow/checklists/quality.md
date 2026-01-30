# Requirements Quality Checklist: ScholarFlow Core Workflow

**Purpose**: Validate the quality, clarity, and completeness of the core workflow requirements before implementation.
**Created**: 2026-01-27
**Feature**: [specs/001-core-workflow/spec.md]

## Requirement Completeness
- [x] CHK001 Are the specific fields for author manual fallback explicitly defined? [Completeness, Clarification 2026-01-27]
- [x] CHK002 Are the contents and format of the notification email for "Return for Revision" specified? [Gap, Spec §US2]
- [x] CHK003 Does the spec define the behavior when a manuscript is resubmitted after revision? [Gap, Spec §US2]
- [x] CHK004 Are the specific metadata fields for the generated PDF invoice defined? [Completeness, Spec §FR-004]

## Requirement Clarity
- [x] CHK005 Is "Frontiers 风格" quantified with specific layout, spacing, or branding guidelines? [Ambiguity, Spec §US1]
- [x] CHK006 Is the "KPI 归属人" selection criteria clearly defined (e.g., workload balancing, expertise)? [Clarity, Spec §FR-007]
- [x] CHK007 Are the specific "financial legal elements" required for the invoice listed? [Ambiguity, Spec §SC-004]
- [x] CHK008 Is the "manual fallback" trigger condition (e.g., timeout, error code) explicitly defined? [Clarity, Clarification 2026-01-27]

## Scenario & Edge Case Coverage
- [x] CHK009 Are requirements defined for rolling back a "confirmed payment" status if marked in error? [Recovery, Gap]
- [x] CHK010 Are requirements specified for handling expired reviewer tokens during an active session? [Edge Case, Spec §FR-003]
- [x] CHK011 Does the spec define the behavior when the AI recommendation engine returns zero results? [Exception Flow, Gap]
- [x] CHK012 Are requirements defined for revoking an already sent reviewer invitation? [Recovery, Gap]

## Consistency & Measurability
- [x] CHK013 Are the status labels consistent between the Spec, Plan, and Data Model (e.g., `returned_for_revision` vs `returned`)? [Consistency, Data Model]
- [x] CHK014 Can the "85% accuracy" for AI extraction be objectively measured against a golden dataset? [Measurability, Spec §SC-001]
- [x] CHK015 Can the "3-second PDF preview" requirement be verified across different network conditions? [Measurability, Spec §SC-002]

## Non-Functional Requirements
- [x] CHK016 Are security requirements defined for protecting the "long-lived JWT" from interception? [Security, Plan]
- [x] CHK017 Are logging requirements defined for audit trails of financial status changes? [Observability, Plan]
- [x] CHK018 Are data retention requirements specified for rejected or expired manuscripts? [Gap]