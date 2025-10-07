import React from "react";
import Skeleton from "react-loading-skeleton";
import "react-loading-skeleton/dist/skeleton.css";

// General-purpose skeleton layout
const GeneralSkeleton = () => (
  <div className="w-full max-w-4xl mx-auto px-4 py-16 space-y-10">
    {/* Header */}
    <Skeleton height={40} width="60%" className="mb-4" />
    {/* Subheader */}
    <Skeleton height={24} width="40%" className="mb-8" />
    {/* Paragraphs */}
    <Skeleton count={3} height={16} className="mb-2" />
    {/* Card grid */}
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6 mt-8">
      {[...Array(3)].map((_, i) => (
        <div
          key={i}
          className="p-4 rounded-lg bg-white dark:bg-gray-800 shadow flex flex-col items-center"
        >
          <Skeleton circle height={56} width={56} className="mb-4" />
          <Skeleton height={20} width="80%" className="mb-2" />
          <Skeleton height={14} width="60%" />
        </div>
      ))}
    </div>
  </div>
);

const Loader = ({ skeleton }) => {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center min-h-screen bg-[#dfe4ec] dark:bg-[#23201d] transition-colors">
      {skeleton ? skeleton : <GeneralSkeleton />}
    </div>
  );
};

export default Loader;
