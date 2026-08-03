// Shared types between the dashboard and the API.

export interface Summary {
  suppliers: number;
  orders: number;
  calls: number;
  last_call_at: string | null;
  pending_orders: number;
}

export interface Supplier {
  id: string;
  name: string;
  phone: string;
  city: string;
  state: string;
  pincode: string;
  contact_person: string;
  gstin: string;
}

export interface StockItem {
  sku: string;
  name: string;
  warehouse: string;
  quantity: number;
  pack_size: string;
  mrp_inr: number;
}

export interface OrderItem {
  sku: string;
  quantity: number;
}

export interface Order {
  id: string;
  supplier_id: string;
  status: string;
  items: OrderItem[];
  total_qty: number;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface Shipment {
  id: string;
  order_id: string;
  status: string;
  carrier: string;
  tracking_no: string;
  expected_delivery: string | null;
  last_update: string;
  history: Array<{ at: string; status: string; note: string }>;
}

export interface CallTurn {
  role: "caller" | "agent";
  text: string;
  at: string;
}

export interface CallAction {
  name: string;
  args: Record<string, any>;
  result?: any;
  at: string;
}

export type ResolutionStatus = "resolved" | "partial" | "unresolved" | "";
export type Satisfaction = "happy" | "neutral" | "unhappy" | "";

export interface Call {
  id: string;
  started_at: string;
  ended_at: string | null;
  duration_sec: number;
  supplier_id: string | null;
  caller_phone: string;
  caller_name: string;
  language: string;
  intent: string;
  outcome: string;
  escalated: boolean;
  transcript: CallTurn[];
  actions: CallAction[];
  // Structured call-outcome fields (may be empty string/null for old rows)
  reason: string;
  solution: string;
  resolution_status: ResolutionStatus;
  satisfaction: Satisfaction;
  follow_up_required: boolean;
  staff_resolution: string;
  staff_resolved_at: string | null;
  sheet_synced: boolean;
  verified: boolean;
}
