import Link from "next/link";
import { Card, PageHead } from "@/components/dash/DataBadge";
import { SettingsForm } from "@/components/dash/SettingsForm";
import { getDefaultSymbol } from "@/lib/actions";
import { getUser } from "@/lib/session";

export const metadata = { title: "Settings" };

export default async function Page() {
  const [user, current] = await Promise.all([getUser(), getDefaultSymbol()]);
  return (
    <>
      <PageHead title="Settings" source="sample" sub="Accounts are optional and only store your watchlist and default symbol." />
      <Card className="max-w-md p-5">
        {user ? (
          <SettingsForm current={current} />
        ) : (
          <p className="text-sm text-muted">
            <Link href="/sign-in" className="text-accent">Sign in</Link> or <Link href="/sign-up" className="text-accent">create a free account</Link> to save settings.
          </p>
        )}
      </Card>
    </>
  );
}
