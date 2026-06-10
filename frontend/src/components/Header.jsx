/**
 * Header.jsx — Top navigation bar for QueryFlow.
 */
export default function Header() {
  return (
    <header className="header" role="banner">
      <div className="header-left">
        <h1 className="header-title">QueryFlow</h1>
        <p className="header-subtitle">
          Enterprise Demo · Medallion Architecture (dbt) · ClickHouse + LangGraph
        </p>
      </div>
      <div className="header-badges" role="status" aria-label="System status">
        <div className="badge badge-green">
          <div className="badge-dot" aria-hidden="true" />
          ClickHouse
        </div>
        <div className="badge badge-cyan">
          <div className="badge-dot" aria-hidden="true" />
          dbt
        </div>
        <div className="badge badge-purple">
          <div className="badge-dot" aria-hidden="true" />
          Airflow
        </div>
      </div>
    </header>
  );
}
