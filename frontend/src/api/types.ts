export type ApiError = { error: string; message: string };

export type Business = {
  id: string;
  name: string;
  slug: string;
  phone: string | null;
  timezone: string;
  slot_step_min: number;
};

export type PublicBusiness = Pick<Business, "name" | "slug" | "phone" | "timezone"> & { assistant_enabled?: boolean };

export type PublicService = { id: string; name: string; duration_min: number; price: number };

export type Service = PublicService & { is_active: boolean };

export type SlotsResponse = { date: string; slots: string[] };

export type BookingRequest = { service_id: string; start_time: string; name: string; phone: string };

export type BookingResponse = {
  booking_id: string;
  service: string;
  start_time: string;
  end_time: string;
  status: AppointmentStatus;
  message: string;
};

export type AppointmentStatus = "booked" | "completed" | "cancelled" | "no_show";

export type Appointment = {
  id: string;
  booking_id: string;
  start_time: string;
  end_time: string;
  status: AppointmentStatus;
  customer_name: string;
  customer_phone: string;
  service_id: string;
  service_name: string;
  price: number;
  whatsapp_url: string;
};

export type TodaySummary = {
  date: string;
  business_name: string;
  count: number;
  no_shows: number;
  revenue_estimate: number;
};

export type WorkingHour = { weekday: number; open_time: string; close_time: string };

export type Stats = {
  month: string;
  total: number;
  completed: number;
  no_show: number;
  cancelled: number;
  no_show_rate: number;
  revenue_estimate: number;
  busiest_weekday: string | null;
};

export type AssistantTurn = { role: "user" | "assistant"; content: string };
export type AssistantReply = { reply: string; service_id: string | null; date: string | null; slots: string[] };
