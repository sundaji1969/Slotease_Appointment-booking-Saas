import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { apiError } from "../../api/client";
import { login } from "../../api/endpoints";
import { Button, Field } from "../../components/ui";
import { setToken } from "../../lib/auth";
import { AuthShell } from "./AuthShell";

const schema = z.object({
  email: z.string().trim().email("Enter a valid email"),
  password: z.string().min(1, "Enter your password"),
});
type Values = z.infer<typeof schema>;

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState } = useForm<Values>({ resolver: zodResolver(schema) });

  async function onSubmit(v: Values) {
    setError(null);
    try {
      const { access_token } = await login(v.email, v.password);
      setToken(access_token);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from?.startsWith("/dashboard") ? from : "/dashboard", { replace: true });
    } catch (err) {
      setError(apiError(err).message);
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle={
        <>
          New here?{" "}
          <Link to="/register" className="font-semibold text-brand-700">
            Create your booking page
          </Link>
        </>
      }
    >
      <form noValidate onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Field label="Email" type="email" autoComplete="email" error={formState.errors.email?.message} {...register("email")} />
        <Field
          label="Password"
          type="password"
          autoComplete="current-password"
          error={formState.errors.password?.message}
          {...register("password")}
        />
        {error && (
          <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
            {error}
          </p>
        )}
        <Button type="submit" className="min-h-12 w-full" disabled={formState.isSubmitting}>
          {formState.isSubmitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </AuthShell>
  );
}
