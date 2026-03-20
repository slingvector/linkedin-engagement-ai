export default function Home() {
  return (
    <div className="flex h-full flex-col items-center justify-center space-y-4">
      <h1 className="text-4xl font-bold">Welcome to LinkedIn Copilot</h1>
      <p className="text-muted-foreground text-lg text-center max-w-[600px]">
        Select "Post Creator" to generate high-converting LinkedIn posts, or "Creator Radar" 
        to track industry leaders and generate smart comment strategies.
      </p>
    </div>
  );
}
