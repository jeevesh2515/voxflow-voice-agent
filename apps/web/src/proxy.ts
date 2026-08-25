import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

const publicRoutes = ["/sign-in", "/sign-up", "/", "/pricing", "/about", "/onboarding"];

export async function proxy(request: NextRequest) {
  const response = NextResponse.next();

  const isPublicRoute = publicRoutes.some((route) =>
    request.nextUrl.pathname === route || request.nextUrl.pathname.startsWith(route + "/")
  );

  const isApiRequest = request.nextUrl.pathname.startsWith("/api/") || request.headers.get("accept") === "application/json";
  const demoCookie = request.cookies.get("voxflow_demo_user");
  let hasScopedDemoSession = false;
  try {
    const demo = demoCookie?.value ? JSON.parse(decodeURIComponent(demoCookie.value)) : null;
    hasScopedDemoSession = demo?.tenant_id === "varun" && demo?.email === "demo@voxflow.invalid";
  } catch {
    hasScopedDemoSession = false;
  }

  try {
    const supabase = await createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();

    // The cookie is only a UX gate for the explicitly fixed demo tenant. The
    // backend independently limits it to read-only APIs and never accepts it as
    const authToken = request.cookies.get("auth-token");
    const isAuthenticated = !!session || !!authToken || (hasScopedDemoSession && !isApiRequest);

    if (!isAuthenticated && !isPublicRoute) {
      if (isApiRequest) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
      }
      const url = request.nextUrl.clone();
      url.pathname = "/sign-in";
      return NextResponse.redirect(url);
    }

    if (isAuthenticated && (request.nextUrl.pathname === "/sign-in" || request.nextUrl.pathname === "/sign-up")) {
      const url = request.nextUrl.clone();
      url.pathname = "/dashboard";
      return NextResponse.redirect(url);
    }
  } catch {
    const authToken = request.cookies.get("auth-token");
    const isAuth = !!authToken || hasScopedDemoSession;
    if (!isAuth && !isPublicRoute) {
      const url = request.nextUrl.clone();
      url.pathname = "/sign-in";
      return NextResponse.redirect(url);
    }
  }

  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
