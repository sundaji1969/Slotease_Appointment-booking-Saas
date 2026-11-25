import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";

import BookingPage from "../src/pages/public/BookingPage";
import { API, server } from "./server";
import { renderAt } from "./utils";

const SLOT_A = "2026-10-10T17:30:00+05:30";
const SLOT_B = "2026-10-10T18:15:00+05:30";

let slotCalls = 0;
let bookingBodies: unknown[] = [];

function baseHandlers() {
  return [
    http.get(`${API}/public/glow-salon`, () =>
      HttpResponse.json({ name: "Glow Salon", slug: "glow-salon", phone: "+919876543210", timezone: "Asia/Kolkata" }),
    ),
    http.get(`${API}/public/glow-salon/services`, () =>
      HttpResponse.json([
        { id: "s1", name: "Haircut", duration_min: 30, price: 300 },
        { id: "s3", name: "Haircut + Beard", duration_min: 45, price: 420 },
      ]),
    ),
    http.get(`${API}/public/glow-salon/slots`, () => {
      slotCalls += 1;
      return HttpResponse.json({ date: "2026-10-10", slots: slotCalls === 1 ? [SLOT_A, SLOT_B] : [SLOT_B] });
    }),
  ];
}

beforeEach(() => {
  slotCalls = 0;
  bookingBodies = [];
  server.use(...baseHandlers());
});

async function pickServiceAndSlot(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole("radio", { name: /Haircut \+ Beard/ }));
  await user.click(await screen.findByRole("radio", { name: "5:30 PM" }));
}

describe("public booking page", () => {
  it("books a slot end to end and shows the confirmation", async () => {
    server.use(
      http.post(`${API}/public/glow-salon/bookings`, async ({ request }) => {
        bookingBodies.push(await request.json());
        return HttpResponse.json(
          {
            booking_id: "APT-20261010-0007",
            service: "Haircut + Beard",
            start_time: SLOT_A,
            end_time: "2026-10-10T18:15:00+05:30",
            status: "booked",
            message: "Booking confirmed at Glow Salon, Sat 10 Oct, 5:30 PM",
          },
          { status: 201 },
        );
      }),
    );
    const user = userEvent.setup();
    renderAt("/glow-salon", "/:slug", <BookingPage />);

    expect(await screen.findByRole("heading", { name: "Glow Salon" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm booking" })).toBeDisabled();

    await pickServiceAndSlot(user);
    await user.type(screen.getByLabelText("Name"), "Ravi Kumar");
    await user.type(screen.getByLabelText("Mobile number"), "9123456780");
    await user.click(screen.getByRole("button", { name: "Confirm booking" }));

    expect(await screen.findByText("You're booked!")).toBeInTheDocument();
    expect(screen.getByText("APT-20261010-0007")).toBeInTheDocument();
    expect(screen.getByText("Sat 10 Oct, 5:30 PM")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Add to WhatsApp" })).toHaveAttribute(
      "href",
      expect.stringContaining("https://wa.me/919876543210?text="),
    );
    expect(bookingBodies).toEqual([{ service_id: "s3", start_time: SLOT_A, name: "Ravi Kumar", phone: "9123456780" }]);
  });

  it("on 409 shows a toast, refetches slots and keeps the customer's details", async () => {
    server.use(
      http.post(`${API}/public/glow-salon/bookings`, () =>
        HttpResponse.json(
          { error: "SLOT_TAKEN", message: "This slot was just booked. Please pick another time." },
          { status: 409 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderAt("/glow-salon", "/:slug", <BookingPage />);
    await pickServiceAndSlot(user);
    await user.type(screen.getByLabelText("Name"), "Ravi Kumar");
    await user.type(screen.getByLabelText("Mobile number"), "9123456780");
    await user.click(screen.getByRole("button", { name: "Confirm booking" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("This slot was just booked. Please pick another time.");
    await waitFor(() => expect(slotCalls).toBe(2));
    expect(await screen.findByRole("radio", { name: "6:15 PM" })).toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: "5:30 PM" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toHaveValue("Ravi Kumar");
    expect(screen.getByLabelText("Mobile number")).toHaveValue("9123456780");
    expect(screen.getByRole("button", { name: "Confirm booking" })).toBeDisabled(); // must re-pick a slot
  });

  it("shows validation messages for bad name and phone", async () => {
    const user = userEvent.setup();
    renderAt("/glow-salon", "/:slug", <BookingPage />);
    await pickServiceAndSlot(user);
    await user.type(screen.getByLabelText("Name"), "R");
    await user.type(screen.getByLabelText("Mobile number"), "12345");
    await user.click(screen.getByRole("button", { name: "Confirm booking" }));

    expect(await screen.findByText("Please enter your name (at least 2 characters)")).toBeInTheDocument();
    expect(screen.getByText("Enter a valid 10-digit mobile number")).toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toHaveAttribute("aria-invalid", "true");
  });

  it("shows an empty state when there are no free slots", async () => {
    server.use(http.get(`${API}/public/glow-salon/slots`, () => HttpResponse.json({ date: "2026-10-12", slots: [] })));
    const user = userEvent.setup();
    renderAt("/glow-salon", "/:slug", <BookingPage />);
    await user.click(await screen.findByRole("radio", { name: /^Haircut30 min/ }));
    expect(await screen.findByText("No free slots — try another day")).toBeInTheDocument();
  });

  it("assistant suggestions fill service, day and time; hidden when disabled", async () => {
    const asked: unknown[] = [];
    server.use(
      http.get(`${API}/public/glow-salon`, () =>
        HttpResponse.json({
          name: "Glow Salon",
          slug: "glow-salon",
          phone: "+919876543210",
          timezone: "Asia/Kolkata",
          assistant_enabled: true,
        }),
      ),
      http.post(`${API}/public/glow-salon/assistant`, async ({ request }) => {
        asked.push(await request.json());
        return HttpResponse.json({
          reply: "Free Haircut + Beard times on Sat 10 Oct — tap one to book:",
          service_id: "s3",
          date: "2026-10-10",
          slots: [SLOT_A, SLOT_B],
        });
      }),
    );
    const user = userEvent.setup();
    renderAt("/glow-salon", "/:slug", <BookingPage />);
    await screen.findByRole("radio", { name: /Haircut \+ Beard/ });
    await user.type(screen.getByLabelText("Describe what you'd like to book"), "haircut and beard saturday evening");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText(/Free Haircut \+ Beard times/)).toBeInTheDocument();
    expect(asked).toEqual([{ message: "haircut and beard saturday evening", history: [] }]);
    await user.click(screen.getByRole("button", { name: "Sat 10 Oct · 5:30 PM" }));

    expect(screen.getByRole("radio", { name: /Haircut \+ Beard/ })).toHaveAttribute("aria-checked", "true");
    expect(await screen.findByText(/Haircut \+ Beard · Sat 10 Oct, 5:30 PM/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm booking" })).toBeEnabled();
  });

  it("does not show the assistant when it is not enabled", async () => {
    renderAt("/glow-salon", "/:slug", <BookingPage />);
    await screen.findByRole("heading", { name: "Glow Salon" });
    expect(screen.queryByLabelText("Booking assistant")).not.toBeInTheDocument();
  });

  it("shows a friendly message for an unknown business", async () => {
    server.use(
      http.get(`${API}/public/nope-biz`, () =>
        HttpResponse.json({ error: "BUSINESS_NOT_FOUND", message: "Business not found" }, { status: 404 }),
      ),
    );
    renderAt("/nope-biz", "/:slug", <BookingPage />);
    expect(await screen.findByRole("heading", { name: "Business not found" })).toBeInTheDocument();
  });
});
