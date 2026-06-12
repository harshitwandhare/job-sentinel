import { redirect } from "next/navigation";

/**
 * Legacy route: the partial editor that lived here is superseded by the
 * integrated view/edit screen at /profile. Redirect to keep old links alive.
 */
export default function ProfileEditPage() {
  redirect("/profile");
}
