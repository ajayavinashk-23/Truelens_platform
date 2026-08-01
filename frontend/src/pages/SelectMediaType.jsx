import { useNavigate, useSearchParams } from "react-router-dom";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import ProgressSteps from "../components/ProgressSteps";
import MediaTypeCard from "../components/MediaTypeCard";
import { MEDIA_TYPE_LIST } from "../lib/mediaTypes";

export default function SelectMediaType() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const preselected = searchParams.get("type");

  return (
    <div className="flex min-h-screen flex-col bg-surface">
      <Navbar />

      <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-14">
        <ProgressSteps current={1} />

        <div className="mt-10 max-w-lg">
          <h1 className="font-display text-3xl font-bold text-ink">
            What are you verifying?
          </h1>
          <p className="mt-2 text-sm text-ink-secondary">
            Choose a media type to load the right detection pipeline. You can
            switch types at any time before uploading.
          </p>
        </div>

        <div className="mt-9 grid gap-5 sm:grid-cols-3">
          {MEDIA_TYPE_LIST.map((type) => (
            <MediaTypeCard
              key={type.id}
              icon={type.icon}
              title={type.title}
              description={type.description}
              highlighted={preselected === type.id}
              onClick={() => navigate(`/upload?type=${type.id}`)}
            />
          ))}
        </div>
      </main>

      <Footer />
    </div>
  );
}
