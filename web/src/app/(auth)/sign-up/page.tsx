import { AuthForm } from "@/components/AuthForm";
import { signUp } from "@/lib/actions";
export const metadata = { title: "Create account" };
export default function Page() { return <AuthForm mode="up" action={signUp} />; }
