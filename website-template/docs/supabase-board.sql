-- 게시판 테이블과 보안 규칙 (Supabase SQL Editor 에 붙여 넣고 Run)
-- 방문자는 글을 올릴 수 있지만 승인 전에는 보이지 않습니다.
-- 로그인한 관리자만 승인하거나 지울 수 있습니다. 공개 가입은 끄세요 (연결-가이드.md 3단계).

create table if not exists public.board_posts (
  id bigint generated always as identity primary key,
  title text not null check (char_length(title) between 1 and 100),
  body text not null check (char_length(body) between 1 and 2000),
  author_name text check (author_name is null or char_length(author_name) <= 30),
  approved boolean not null default false,
  created_at timestamptz not null default now()
);

alter table public.board_posts enable row level security;

-- 누구나 승인된 글을 읽을 수 있습니다.
create policy "승인된 글 읽기" on public.board_posts
  for select using (approved = true);

-- 누구나 글을 올릴 수 있지만, 처음부터 승인된 상태로는 올릴 수 없습니다.
create policy "글 올리기 (승인 전)" on public.board_posts
  for insert with check (approved = false);

-- 로그인한 관리자는 승인 대기 글도 볼 수 있습니다 (관리자 화면이 이 규칙을 씁니다).
create policy "관리자는 모든 글 읽기" on public.board_posts
  for select using (auth.role() = 'authenticated');

-- 로그인한 관리자만 승인하거나 고칠 수 있습니다.
create policy "관리자만 승인과 수정" on public.board_posts
  for update using (auth.role() = 'authenticated')
  with check (auth.role() = 'authenticated');

-- 로그인한 관리자만 지울 수 있습니다.
create policy "관리자만 삭제" on public.board_posts
  for delete using (auth.role() = 'authenticated');
