export interface AnalystContext {
  source_type: string;
  title: string;
  content: string;
  relevance: number;
}

export interface AnalystRange {
  from: string;
  to: string;
}

export interface AnalystChatRequest {
  session_id: string;
  user_message: string;
  preferred_range?: AnalystRange;
}

export interface AnalystChatResponse {
  session_id: string;
  answer: string;
  contexts: AnalystContext[];
}

export interface AutoCommentModuleContribution {
  name: string;
  value: number;
}

export interface AutoCommentRequest {
  date: string;
  lsi: number;
  status: string;
  module_contributions: AutoCommentModuleContribution[];
  active_flags: string[];
  upcoming_events: string[];
}

export interface AutoCommentResponse {
  comment: string;
  retrospective: string;
  outlook: string;
}
