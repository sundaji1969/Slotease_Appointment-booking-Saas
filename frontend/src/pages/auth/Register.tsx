import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";

import { apiError } from "../../api/client";
import { register as registerApi } from "../../api/endpoints";
import { Button, Field } from "../../components/ui";
import { setToken } from "../../lib/auth";
import { AuthShell } from "./AuthShell";

const RESERVED = ["login", "register", "dashboard", "api", "admin", "public", "auth", "docs", "health", "static", "assets"];

const schema = z.object({
  business_name: z.string().trim().min(2, "Business name is too short").max(80),
  slug: z
    .string()
    .trim()
    .regex(/^[a-z0-9-]{3,40}$/, "3–40 characters: lowercase letters, numbers and hyphens")
    .refine((s) => !RESERVED.includes(s), "That link is reserved"),
  email: z.string().trim().email("Enter a valid email"),
  password: z.string().min(8, "At least 8 characters"),
  phone: z
    .string()
    .trim()
    .regex(/^([6-9]\d{9})?$/, "Enter a valid 10-digit mobile number"),
});
type Values = z.infer<typeof schema>;

function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40);
}

export default function Register() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState, setValue, getFieldState, control } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { business_name: "", slug: "", email: "", password: "", phone: "" },
  });
  const slug = useWatch({ control, name: "slug" });

  async function onSubmit(v: Values) {
    setError(null);
    try {
      const res = await registerApi({ ...v, phone: v.phone || undefined });
      setToken(res.access_token);
      navigate("/dashboard/services", { replace: true });
    } catch (err) {
      setError(apiError(err).message);
    }
  }

  const nameField = register("business_name");

  return (
    <AuthShell
      title="Create your booking page"
      subtitle={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-semibold text-brand-700">
            Sign in
          </Link>
        </>
      }
    >
      <form noValidate onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Field
          label="Business name"
          placeholder="Glow Salon"
          error={formState.errors.business_name?.message}
          {...nameField}
          onChange={(e) => {
            nameField.onChange(e);
            if (!getFieldState("slug").isDirty) setValue("slug", slugify(e.target.value));
          }}
        />
        <Field
          label="Booking link"
          prefix="slotease.app/"
          placeholder="glow-salon"
          hint={slug ? `Customers book at /${slug}` : undefined}
          error={formState.errors.slug?.message}
          {...register("slug")}
        />
        <Field label="Email" type="email" autoComplete="email" error={formState.errors.email?.message} {...register("email")} />
        <Field
          label="Password"
          type="password"
          autoComplete="new-password"
          error={formState.errors.password?.message}
          {...register("password")}
        />
        <Field
          label="Business WhatsApp number (optional)"
          type="tel"
          inputMode="numeric"
          prefix="+91"
          maxLength={10}
          error={formState.errors.phone?.message}
          {...register("phone")}
        />
        {error && (
          <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
            {error}
          </p>
        )}
        <Button type="submit" className="min-h-12 w-full" disabled={formState.isSubmitting}>
          {formState.isSubmitting ? "Creating…" : "Create account"}
        </Button>
        <p className="text-center text-xs text-slate-500">₹499/month after your free trial. Cancel anytime.</p>
      </form>
    </AuthShell>
  );
}
