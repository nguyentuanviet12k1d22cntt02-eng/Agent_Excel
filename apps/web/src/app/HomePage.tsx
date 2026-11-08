import { PageHeader } from "@/components/PageHeader";
import { useCurrentUser } from "@/features/auth/authContext";

const WORKFLOW = [
  "Tải giáo trình (PDF, DOCX) để AI trích dẫn khi viết gợi ý.",
  "Tạo bài tập: file đề, file đáp án cùng bố cục, sheet làm bài.",
  "Bấm “Sinh kịch bản”: AI chia bước và viết gợi ý, hệ thống tự kiểm trên file đề và đáp án.",
  "Xem, sửa từng bước rồi gửi duyệt và duyệt.",
  "Phát hành và tải file đề đã nhúng mã bài để phát cho học viên.",
];

export function HomePage() {
  const user = useCurrentUser();
  return (
    <>
      <PageHeader
        title={`Xin chào, ${user.full_name}`}
        subtitle="Quy trình chuẩn bị một bài thực hành có gia sư"
      />
      <ol className="workflow">
        {WORKFLOW.map((text) => (
          <li key={text}>{text}</li>
        ))}
      </ol>
    </>
  );
}
