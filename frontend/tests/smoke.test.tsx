import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { formatBookingDate, formatINR, formatTime } from "../src/lib/format";
import { addDays, startOfWeek, weekdayIndex } from "../src/lib/dates";
import Home from "../src/pages/Home";
import { renderAt } from "./utils";

describe("smoke", () => {
  it("renders the landing page", () => {
    renderAt("/", "/", <Home />);
    expect(screen.getByRole("link", { name: "Create your booking page" })).toHaveAttribute("href", "/register");
  });

  it("formats money and times the Indian way", () => {
    expect(formatINR(6450)).toBe("₹6,450");
    expect(formatINR(150000)).toBe("₹1,50,000");
    expect(formatTime("2026-10-10T12:00:00Z", "Asia/Kolkata")).toBe("5:30 PM");
    expect(formatBookingDate("2026-10-10T17:30:00+05:30", "Asia/Kolkata")).toBe("Sat 10 Oct, 5:30 PM");
  });

  it("date helpers use Monday = 0", () => {
    expect(weekdayIndex("2026-10-12")).toBe(0); // Monday
    expect(weekdayIndex("2026-10-11")).toBe(6); // Sunday
    expect(startOfWeek("2026-10-10")).toBe("2026-10-05");
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
  });
});
