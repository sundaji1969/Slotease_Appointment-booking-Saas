import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { addBreak, fromWeek, toWeek, validateWeek, type Week } from "../src/lib/hours";
import { HoursForm } from "../src/pages/dashboard/Hours";
import { API, server } from "./server";
import { renderAt } from "./utils";

const closedWeek = (): Week => Array.from({ length: 7 }, () => ({ closed: true, windows: [] }));

describe("working hours logic", () => {
  it("round-trips API rows <-> week model", () => {
    const rows = [
      { weekday: 1, open_time: "14:00:00", close_time: "20:00:00" },
      { weekday: 1, open_time: "10:00:00", close_time: "13:00:00" },
    ];
    const week = toWeek(rows);
    expect(week[0].closed).toBe(true);
    expect(week[1]).toEqual({ closed: false, windows: [{ open: "10:00", close: "13:00" }, { open: "14:00", close: "20:00" }] });
    expect(fromWeek(week)).toEqual([
      { weekday: 1, open_time: "10:00", close_time: "13:00" },
      { weekday: 1, open_time: "14:00", close_time: "20:00" },
    ]);
  });

  it("validates order, overlap and empty open days", () => {
    const w = closedWeek();
    w[0] = { closed: false, windows: [{ open: "13:00", close: "10:00" }] };
    w[1] = { closed: false, windows: [{ open: "10:00", close: "13:00" }, { open: "12:00", close: "15:00" }] };
    w[2] = { closed: false, windows: [] };
    w[3] = { closed: false, windows: [{ open: "10:00", close: "13:00" }, { open: "13:00", close: "18:00" }] };
    expect(validateWeek(w)).toEqual({
      0: "Closing time must be after opening time",
      1: "Time windows overlap",
      2: "Add opening hours or mark the day closed",
    });
  });

  it("add break splits a long window", () => {
    expect(addBreak({ closed: false, windows: [{ open: "10:00", close: "20:00" }] }).windows).toEqual([
      { open: "10:00", close: "14:30" },
      { open: "15:30", close: "20:00" },
    ]);
  });
});

describe("hours form", () => {
  it("blocks save with an inline error and sends ONE PUT when valid", async () => {
    const puts: unknown[] = [];
    server.use(
      http.put(`${API}/working-hours`, async ({ request }) => {
        const body = await request.json();
        puts.push(body);
        return HttpResponse.json(body);
      }),
    );
    const user = userEvent.setup();
    renderAt("/h", "/h", <HoursForm initial={[{ weekday: 0, open_time: "10:00:00", close_time: "18:00:00" }]} />);

    const closes = screen.getByLabelText("Monday window 1 closes");
    await user.clear(closes);
    await user.type(closes, "09:00");
    await user.click(screen.getByRole("button", { name: "Save hours" }));
    expect(await screen.findByText("Closing time must be after opening time")).toBeInTheDocument();
    expect(puts).toHaveLength(0);

    await user.clear(closes);
    await user.type(closes, "19:00");
    await user.click(screen.getByRole("button", { name: "Save hours" }));
    expect(await screen.findByText("Working hours saved")).toBeInTheDocument();
    expect(puts).toEqual([[{ weekday: 0, open_time: "10:00", close_time: "19:00" }]]);
  });
});
