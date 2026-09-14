"""Seeds the local database with a handful of realistic sample jobs so the
"Öner" flow has something to show — useful for screenshots/demos without
spending Apify credits. Safe to run repeatedly; only inserts jobs whose id
isn't already in the database.
"""

from datetime import datetime, timedelta, timezone

from src.preprocessing.schema import Job
from src.model.embeddings import embed_texts
from src.db.storage import save_new_jobs

now = datetime.now(timezone.utc)


def days_ago(n: int) -> str:
    return (now - timedelta(days=n)).isoformat()


JOBS = [
    Job(
        id="demo:linkedin:1",
        source="linkedin",
        title="Senior Full Stack Developer",
        company="TechNova",
        location="Istanbul, Turkey",
        country="tr",
        description="We're looking for a Senior Full Stack Developer with strong React and Node.js experience to join our product team. You'll own features end to end, from API design to a polished UI.",
        url="https://linkedin.com/jobs/view/demo-1",
        remote=False,
        employment_type="Full-time",
        salary="₺60.000 - ₺85.000",
        posted_date=days_ago(1),
    ),
    Job(
        id="demo:indeed:1",
        source="indeed",
        title="Full Stack Engineer (React / Node)",
        company="Globex Inc.",
        location="Remote, United States",
        country="us",
        description="Globex is hiring a Full Stack Engineer comfortable across React, Node.js and PostgreSQL. Fully remote, async-first team.",
        url="https://indeed.com/viewjob?jk=demo-2",
        remote=True,
        employment_type="Full-time",
        salary="$95,000 - $120,000",
        posted_date=days_ago(2),
    ),
    Job(
        id="demo:kariyer:1",
        source="kariyer",
        title="Backend Developer (.NET)",
        company="Vestel",
        location="İzmir, Türkiye",
        country="tr",
        description=".NET Core ve mikroservis mimarisi tecrübesi olan bir Backend Developer arıyoruz. Takımımızda kod incelemesi ve CI/CD süreçlerine aktif katılım bekleniyor.",
        url="https://kariyer.net/is-ilani/demo-3",
        remote=False,
        employment_type="Tam zamanlı",
        posted_date=days_ago(3),
    ),
    Job(
        id="demo:upwork:1",
        source="upwork",
        title="Frontend Developer - React",
        company="Private Client",
        location="Remote",
        country=None,
        description="Looking for a freelance React developer to rebuild our dashboard UI. 3-month contract, possibility to extend.",
        url="https://upwork.com/jobs/demo-4",
        remote=True,
        employment_type="Contract",
        posted_date=days_ago(1),
    ),
    Job(
        id="demo:glassdoor:1",
        source="glassdoor",
        title="Full Stack Developer",
        company="Booking.com",
        location="Amsterdam, Netherlands",
        country="nl",
        description="Join our platform team to build customer-facing features used by millions of travelers, working across a React frontend and Java backend.",
        url="https://glassdoor.com/job-listing/demo-5",
        remote=False,
        employment_type="Full-time",
        salary="€55,000 - €70,000",
        posted_date=days_ago(4),
    ),
    Job(
        id="demo:remoteok:1",
        source="remoteok",
        title="Full Stack JavaScript Developer",
        company="Nimbus Labs",
        location="Remote",
        country=None,
        description="Small remote-first startup looking for a full stack JavaScript developer (Next.js + Node) to help ship our MVP.",
        url="https://remoteok.com/remote-jobs/demo-6",
        remote=True,
        employment_type="Full-time",
        posted_date=days_ago(2),
    ),
    Job(
        id="demo:eleman:1",
        source="eleman",
        title="Muhasebe Uzmanı",
        company="Yerel Ticaret A.Ş.",
        location="Bursa, Türkiye",
        country="tr",
        description="Şirketimiz bünyesinde görevlendirilmek üzere en az 3 yıl deneyimli Muhasebe Uzmanı arıyoruz.",
        url="https://eleman.net/is-ilani/demo-7",
        remote=False,
        employment_type="Tam zamanlı",
        posted_date=days_ago(5),
    ),
]


def main():
    titles = [j.title for j in JOBS]
    contents = ["\n".join(p for p in [j.company or "", j.location or "", j.description] if p) for j in JOBS]

    title_vectors = embed_texts(titles)
    content_vectors = embed_texts(contents)

    inserted = save_new_jobs(JOBS, title_vectors, content_vectors)
    print(f"{inserted} demo ilanı eklendi ({len(JOBS)} tanesinden).")


if __name__ == "__main__":
    main()
