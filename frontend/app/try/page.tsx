import ConsultationWorkspace from "../components/ConsultationWorkspace";

export const metadata = {
  title: "Try Volta Memory | Private workspace",
  description: "Try Volta in an isolated private home-energy workspace.",
};

export default function TryPage() {
  return <ConsultationWorkspace mode="try" />;
}
