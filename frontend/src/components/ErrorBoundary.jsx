import { Component } from "react";
import { FileWarning } from "lucide-react";

/**
 * Without this, any uncaught render error (e.g. the backend returning a
 * report shape a component doesn't expect) unmounts the whole React tree
 * and leaves a silent blank page — which looks exactly like "nothing
 * happened" after uploading a file, with no indication anything went
 * wrong. This catches that and shows a recoverable message instead.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("Unhandled error in TrueLens UI:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-surface px-6 text-center">
          <FileWarning size={28} className="text-danger" />
          <h1 className="font-display text-xl font-bold text-ink">
            Something went wrong displaying this page
          </h1>
          <p className="max-w-md text-sm text-ink-secondary">
            {this.state.error.message || "An unexpected error occurred."}
          </p>
          <a
            href="/"
            className="mt-2 text-sm font-medium text-accent-700 hover:text-accent-800"
          >
            Go back to the homepage
          </a>
        </div>
      );
    }
    return this.props.children;
  }
}
