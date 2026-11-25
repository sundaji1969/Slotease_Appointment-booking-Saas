import { useQuery } from "@tanstack/react-query";

import { getMe } from "../api/endpoints";

export function useBusiness() {
  return useQuery({ queryKey: ["me"], queryFn: getMe, staleTime: 5 * 60_000 });
}
