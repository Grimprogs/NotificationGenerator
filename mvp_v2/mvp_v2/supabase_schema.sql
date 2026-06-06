-- Run this in Supabase SQL Editor

-- Table 1: user metadata (import your metadata CSV here)
create table if not exists user_metadata (
  id                  bigserial primary key,
  user_id             text,
  name                text,
  age                 text,
  district_id         text,
  primary_category    text,
  notification_tag    text,
  preferred_language  text,
  mobile_no           text,
  bpl_category        text,
  personal_income_id  text,
  family_income_id    text,
  family_type_id      text
);

-- Table 2: user scores (import your final_table CSV here)
create table if not exists user_scores (
  id                    bigserial primary key,
  user_id               text,
  primary_category      text,
  notification_response text,
  content_score         numeric,
  scheme_score          numeric,
  job_score             numeric,
  service_score         numeric,
  engagement_time_msec  numeric,
  notification_click    numeric
);

-- Table 3: generated notifications (auto-filled by backend)
create table if not exists generated_notifications (
  id                   bigserial primary key,
  user_id              text,
  generated_at         timestamptz,
  segment_key          text,
  notification_number  int,
  title                text,
  body                 text,
  language             text,
  scheme_or_service_id text,
  tone_used            text,
  human_check          text,
  relevance_rationale  text,
  data_signals_used    text
);
