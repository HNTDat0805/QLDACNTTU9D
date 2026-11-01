import { createFileRoute } from "@tanstack/react-router"
import { IntakeService } from "@/client"
import { ActionForm, PageTitle, Panel } from "@/components/Operations/shared"
export const Route = createFileRoute("/_layout/workspace/intake")({
  component: Intake,
})
function Intake() {
  return (
    <section className="max-w-3xl">
      <PageTitle
        title="Tiếp nhận khách vãng lai"
        description="Ghi nhận khách hàng, thiết bị và tình trạng khi bàn giao."
      />
      <Panel title="Phiếu tiếp nhận thiết bị">
        <ActionForm
          fields={[
            { name: "name", label: "Tên khách hàng", required: true },
            {
              name: "phone",
              label: "Số điện thoại",
              type: "tel",
              required: true,
            },
            { name: "brand", label: "Hãng thiết bị", required: true },
            { name: "model", label: "Dòng máy", required: true },
            { name: "imei", label: "IMEI / Số serial" },
            {
              name: "condition",
              label: "Tình trạng ngoại quan",
              required: true,
            },
            { name: "fault", label: "Mô tả lỗi", required: true },
            { name: "accessories", label: "Phụ kiện bàn giao" },
          ]}
          submitLabel="Lưu phiếu tiếp nhận"
          onSubmit={(v) =>
            IntakeService.createDeviceIntake({
              body: {
                customer_name: v.name,
                customer_phone: v.phone,
                brand: v.brand,
                model: v.model,
                imei: v.imei || undefined,
                physical_condition: v.condition,
                fault_description: v.fault,
                accessories_received: v.accessories || undefined,
              },
            })
          }
        />
      </Panel>
    </section>
  )
}
