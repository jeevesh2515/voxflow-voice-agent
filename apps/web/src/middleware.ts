import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

const publicRoutes = ["/sign-in", "/sign-up", "/", "/pricing", "/about"];

export async function middleware(request: NextRequest) {
  const response = NextResponse.next();

  const isPublicRoute = publicRoutes.some((route) =>
    request.nextUrl.pathname === route || request.nextUrl.pathname.startsWith(route + "/")
  );

  const isApiRequest = request.nextUrl.pathname.startsWith("/api/") || request.headers.get("accept") === "application/json";
  const demoCookie = request.cookies.get("voxflow_demo_user");

  try {
    const supabase = await createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();

    const isAuthenticated = !!session || !!demoCookie;

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
  } catch (error) {
    if (!demoCookie && !isPublicRoute) {
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
