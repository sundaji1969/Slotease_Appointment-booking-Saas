import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";

import type { Appointment } from "../src/api/types";
import Today from "../src/pages/dashboard/Today";
import { API, server } from "./server";
import { renderAt } from "./utils";

const appt = (over: Partial<Appointment>): Appointment => ({
  id: "a1",
  booking_id: "APT-20261010-0001",
  start_time: "2026-10-10T17:30:00+05:30",
  end_time: "2026-10-10T18:15:00+05:30",
  status: "booked",
  customer_name: "Ravi Kumar",
  customer_phone: "+919123456780",
  service_id: "s3",
  service_name: "Haircut + Beard",
  price: 420,
  whatsapp_url: "https://wa.me/919123456780?text=hi",
  ...over,
});

let patches: { id: string; body: unknown }[] = [];
let patchStatus = 200;

beforeEach(() => {
  patches = [];
  patchStatus = 200;
  localStorage.setItem("slotease.token", "test-token");
  server.use(
    http.get(`${API}/me`, () =>
      HttpResponse.json({ id: "b1", name: "Glow Salon", slug: "glow-salon", phone: null, timezone: "Asia/Kolkata", slot_step_min: 15 }),
    ),
    http.get(`${API}/dashboard/today`, () =>
      HttpResponse.json({ date: "2026-10-10", business_name: "Glow Salon", count: 12, no_shows: 2, revenue_estimate: 6450 }),
    ),
    http.get(`${API}/appointments`, () =>
      HttpResponse.json([appt({}), appt({ id: "a2", booking_id: "APT-20261010-0002", status: "completed", start_time: "2026-10-10T10:00:00+05:30" })]),
    ),
    http.patch(`${API}/appointments/:id`, async ({ params, request }) => {
      const body = (await request.json()) as { status: Appointment["status"] };
      patches.push({ id: String(params.id), body });
      if (patchStatus !== 200) {
        return HttpResponse.json({ error: "INVALID_TRANSITION", message: "Cannot change" }, { status: patchStatus });
      }
      return HttpResponse.json(appt({ status: body.status }));
    }),
  );
});

describe("owner Today screen", () => {
  it("shows the summary header in the brief's format", async () => {
    renderAt("/dashboard", "/dashboard", <Today />);
    expect(await screen.findByTestId("day-summary")).toHaveTextContent("12 bookings · 2 no-shows · Est. ₹6,450");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("GLOW SALON");
  });

  it("only booked rows have action buttons; Complete sends PATCH and updates the row", async () => {
    const user = userEvent.setup();
    renderAt("/dashboard", "/dashboard", <Today />);
    const row = await screen.findByTestId("appt-APT-20261010-0001");
    const done = await screen.findByTestId("appt-APT-20261010-0002");
    expect(within(done).queryByRole("button", { name: "Complete" })).not.toBeInTheDocument();

    await user.click(within(row).getByRole("button", { name: "Complete" }));
    expect(within(row).getByText("Completed")).toBeInTheDocument(); // optimistic
    await waitFor(() => expect(patches).toEqual([{ id: "a1", body: { status: "completed" } }]));
  });

  it("rolls back the optimistic update when the server rejects it", async () => {
    patchStatus = 422;
    const user = userEvent.setup();
    renderAt("/dashboard", "/dashboard", <Today />);
    const row = await screen.findByTestId("appt-APT-20261010-0001");
    await user.click(within(row).getByRole("button", { name: "No-show" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Cannot change");
    await waitFor(() => expect(within(row).getByText("Booked")).toBeInTheDocument());
  });
});
