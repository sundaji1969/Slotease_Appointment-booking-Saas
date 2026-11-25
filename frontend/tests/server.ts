import { setupServer } from "msw/node";

export const API = "http://localhost:8000";
export const server = setupServer();
