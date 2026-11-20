import { AuthForm } from "@/components/AuthForm";
import { signIn } from "@/lib/actions";
export const metadata = { title: "Sign in" };
export default function Page() { return <AuthForm mode="in" action={signIn} />; }
