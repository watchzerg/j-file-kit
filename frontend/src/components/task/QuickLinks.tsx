import { Link } from "react-router-dom";

const links = [
  {
    title: "配置中心",
    description: "查看并调整 JAV / Raw 任务配置。",
    to: "/config",
  },
  {
    title: "任务列表",
    description: "进入历史 run 浏览页。",
    to: "/tasks",
  },
  {
    title: "文档与帮助",
    description: "参考 docs/FRONTEND_DESIGN.md 与 FE-M1.md。",
    to: null,
  },
] as const;

export default function QuickLinks() {
  return (
    <section className="space-y-4" aria-labelledby="quick-links-heading">
      <h2 id="quick-links-heading" className="font-semibold text-xl">
        快捷入口
      </h2>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {links.map((link) =>
          link.to ? (
            <Link
              key={link.title}
              to={link.to}
              className="rounded-lg border p-5 transition-colors hover:bg-muted/40"
            >
              <QuickLinkContent
                title={link.title}
                description={link.description}
              />
            </Link>
          ) : (
            <div key={link.title} className="rounded-lg border p-5">
              <QuickLinkContent
                title={link.title}
                description={link.description}
              />
            </div>
          ),
        )}
      </div>
    </section>
  );
}

interface QuickLinkContentProps {
  title: string;
  description: string;
}

function QuickLinkContent({ title, description }: QuickLinkContentProps) {
  return (
    <>
      <h3 className="font-semibold">{title}</h3>
      <p className="mt-2 text-muted-foreground text-sm">{description}</p>
    </>
  );
}
