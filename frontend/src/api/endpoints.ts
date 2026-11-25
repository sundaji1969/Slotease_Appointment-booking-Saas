import { api } from "./client";
import type {
  Appointment,
  AssistantReply,
  AssistantTurn,
  AppointmentStatus,
  BookingRequest,
  BookingResponse,
  Business,
  PublicBusiness,
  PublicService,
  Service,
  SlotsResponse,
  Stats,
  TodaySummary,
  WorkingHour,
} from "./types";

// ---------- public ----------
export const getPublicBusiness = (slug: string) =>
  api.get<PublicBusiness>(`/public/${slug}`).then((r) => r.data);
export const getPublicServices = (slug: string) =>
  api.get<PublicService[]>(`/public/${slug}/services`).then((r) => r.data);
export const getSlots = (slug: string, serviceId: string, date: string) =>
  api.get<SlotsResponse>(`/public/${slug}/slots`, { params: { service_id: serviceId, date } }).then((r) => r.data);
export const createBooking = (slug: string, body: BookingRequest) =>
  api.post<BookingResponse>(`/public/${slug}/bookings`, body).then((r) => r.data);

export const askAssistant = (slug: string, message: string, history: AssistantTurn[]) =>
  api.post<AssistantReply>(`/public/${slug}/assistant`, { message, history }).then((r) => r.data);

// ---------- auth ----------
export type RegisterBody = { business_name: string; slug: string; email: string; password: string; phone?: string };
export const register = (body: RegisterBody) =>
  api.post<{ access_token: string; business: Business }>("/auth/register", body).then((r) => r.data);
export const login = (email: string, password: string) =>
  api.post<{ access_token: string }>("/auth/login", { email, password }).then((r) => r.data);

// ---------- owner ----------
export const getMe = () => api.get<Business>("/me").then((r) => r.data);
export const getToday = (date: string) =>
  api.get<TodaySummary>("/dashboard/today", { params: { date } }).then((r) => r.data);
export const getAppointmentsForDay = (date: string) =>
  api.get<Appointment[]>("/appointments", { params: { date } }).then((r) => r.data);
export const getAppointmentsRange = (from: string, to: string) =>
  api.get<Appointment[]>("/appointments", { params: { from, to } }).then((r) => r.data);
export const updateAppointmentStatus = (id: string, status: AppointmentStatus) =>
  api.patch<Appointment>(`/appointments/${id}`, { status }).then((r) => r.data);

export type ServiceBody = { name: string; duration_min: number; price: number };
export const getServices = () => api.get<Service[]>("/services").then((r) => r.data);
export const createService = (body: ServiceBody) => api.post<Service>("/services", body).then((r) => r.data);
export const updateService = (id: string, body: Partial<ServiceBody> & { is_active?: boolean }) =>
  api.put<Service>(`/services/${id}`, body).then((r) => r.data);

export const getHours = () => api.get<WorkingHour[]>("/working-hours").then((r) => r.data);
export const putHours = (rows: WorkingHour[]) => api.put<WorkingHour[]>("/working-hours", rows).then((r) => r.data);

export const getStats = (month: string) => api.get<Stats>("/stats", { params: { month } }).then((r) => r.data);
