import { createBrowserClient } from "@supabase/ssr";

const defaultUrl = "https://gujjyytfpqpkzbrtsink.supabase.co";
const defaultKey = "sb_publishable_5lTf-c4V8Ie_zRHj_qKjCA_ivJyMV8L";

export function createClient() {
  const url =
    process.env.NEXT_PUBLIC_SUPABASE_URL ||
    process.env.SUPABASE_URL ||
    defaultUrl;
  const key =
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
    process.env.SUPABASE_ANON_KEY ||
    defaultKey;

  return createBrowserClient(url, key);
}
