package com.lays.queue;

import org.postgresql.PGConnection;
import org.postgresql.PGNotification;

import java.math.BigDecimal;
import java.sql.*;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class QueueApp {

    private static final String DB_URL = System.getenv().getOrDefault(
            "DB_URL",
            "jdbc:postgresql://localhost:5433/cinema_db"
    );

    private static final String DB_USER = System.getenv().getOrDefault(
            "DB_USER",
            "admin"
    );

    private static final String DB_PASSWORD = System.getenv().getOrDefault(
            "DB_PASSWORD",
            "Mishka"
    );

    private static final Random RANDOM = new Random();

    public static void main(String[] args) throws Exception {
        if (args.length == 0) {
            System.out.println("Usage:");
            System.out.println("  producer <rate_per_second>");
            System.out.println("  worker <worker_id>");
            System.out.println("  monitor");
            return;
        }

        String mode = args[0];

        if ("producer".equals(mode)) {
            int rate = args.length >= 2 ? Integer.parseInt(args[1]) : 100;
            runProducer(rate);
        } else if ("worker".equals(mode)) {
            String workerId = args.length >= 2 ? args[1] : "worker";
            runWorker(workerId);
        } else if ("monitor".equals(mode)) {
            runMonitor();
        } else {
            throw new IllegalArgumentException("Unknown mode: " + mode);
        }
    }

    private static Connection connect() throws SQLException {
        return DriverManager.getConnection(DB_URL, DB_USER, DB_PASSWORD);
    }

    private static void runProducer(int ratePerSecond) throws Exception {
        System.out.println("Producer started, rate = " + ratePerSecond + " tasks/sec");

        long intervalNanos = 1_000_000_000L / ratePerSecond;
        long nextTime = System.nanoTime();
        long counter = 0;

        try (Connection connection = connect()) {
            connection.setAutoCommit(false);

            List<Integer> userIds = loadIds(connection, "users", "user_id");
            List<Integer> movieIds = loadIds(connection, "movie", "movie_id");

            if (userIds.isEmpty()) {
                throw new IllegalStateException("Table users is empty. Add users before running producer.");
            }

            if (movieIds.isEmpty()) {
                throw new IllegalStateException("Table movie is empty. Add movies before running producer.");
            }

            String insertPurchaseSql =
                    "INSERT INTO purchase (user_id, movie_id, purchase_date, price, payment_method) " +
                            "VALUES (?, ?, now(), ?, ?) " +
                            "RETURNING purchase_id";

            String insertTaskSql =
                    "INSERT INTO tasks (task_type, payload, priority) " +
                            "VALUES (?, ?::jsonb, ?)";

            try (
                    PreparedStatement insertPurchase = connection.prepareStatement(insertPurchaseSql);
                    PreparedStatement insertTask = connection.prepareStatement(insertTaskSql);
                    Statement notifyStatement = connection.createStatement()
            ) {
                while (true) {
                    try {
                        boolean critical = RANDOM.nextInt(100) < 20;

                        int priority = critical ? 100 : 0;

                        String taskType = critical
                                ? "SEND_PURCHASE_RECEIPT"
                                : "UPDATE_RECOMMENDATIONS_AFTER_PURCHASE";

                        int userId = userIds.get(RANDOM.nextInt(userIds.size()));
                        int movieId = movieIds.get(RANDOM.nextInt(movieIds.size()));

                        BigDecimal price = new BigDecimal("399.00");
                        String paymentMethod = "card";

                        insertPurchase.setInt(1, userId);
                        insertPurchase.setInt(2, movieId);
                        insertPurchase.setBigDecimal(3, price);
                        insertPurchase.setString(4, paymentMethod);

                        long purchaseId;

                        try (ResultSet rs = insertPurchase.executeQuery()) {
                            rs.next();
                            purchaseId = rs.getLong("purchase_id");
                        }

                        String taskPayload =
                                "{\"purchase_id\":" + purchaseId +
                                        ",\"user_id\":" + userId +
                                        ",\"movie_id\":" + movieId +
                                        ",\"payment_method\":\"" + paymentMethod + "\"" +
                                        ",\"critical\":" + critical + "}";

                        insertTask.setString(1, taskType);
                        insertTask.setString(2, taskPayload);
                        insertTask.setInt(3, priority);
                        insertTask.executeUpdate();

                        notifyStatement.execute("NOTIFY tasks_channel, 'new_task'");

                        connection.commit();

                        counter++;

                        if (counter % ratePerSecond == 0) {
                            System.out.println("Producer inserted total = " + counter);
                        }
                    } catch (Exception e) {
                        connection.rollback();
                        System.out.println("Producer error: " + e.getMessage());
                    }

                    nextTime += intervalNanos;
                    long sleepNanos = nextTime - System.nanoTime();

                    if (sleepNanos > 0) {
                        Thread.sleep(
                                sleepNanos / 1_000_000L,
                                (int) (sleepNanos % 1_000_000L)
                        );
                    }
                }
            }
        }
    }

    private static List<Integer> loadIds(Connection connection, String tableName, String columnName) throws SQLException {
        List<Integer> ids = new ArrayList<>();

        String sql = "SELECT " + columnName + " FROM " + tableName;

        try (Statement statement = connection.createStatement();
             ResultSet rs = statement.executeQuery(sql)) {
            while (rs.next()) {
                ids.add(rs.getInt(columnName));
            }
        }

        connection.rollback();

        return ids;
    }

    private static void runWorker(String workerId) throws Exception {
        System.out.println(workerId + " started");

        try (
                Connection listenConnection = connect();
                Connection workConnection = connect();
                Statement listenStatement = listenConnection.createStatement()
        ) {
            listenStatement.execute("LISTEN tasks_channel");

            PGConnection pgConnection = listenConnection.unwrap(PGConnection.class);

            while (true) {
                int processed = 0;

                while (processOneTask(workConnection, workerId)) {
                    processed++;
                }

                if (processed == 0) {
                    PGNotification[] notifications = pgConnection.getNotifications(1000);

                    if (notifications != null) {
                        System.out.println(workerId + " woke up by NOTIFY");
                    }
                }
            }
        }
    }

    private static boolean processOneTask(Connection connection, String workerId) throws Exception {
        Task task = claimTask(connection, workerId);

        if (task == null) {
            return false;
        }

        System.out.println(workerId + " picked task_id=" + task.taskId +
                ", priority=" + task.priority +
                ", type=" + task.taskType +
                ", attempts=" + task.attempts);

        int sleepMs;

        if (task.priority == 100) {
            sleepMs = 100 + RANDOM.nextInt(200);
        } else {
            sleepMs = 400 + RANDOM.nextInt(500);
        }

        Thread.sleep(sleepMs);

        boolean failed = RANDOM.nextInt(100) < 10;

        if (failed) {
            failTask(connection, task, workerId);
        } else {
            completeTask(connection, task, workerId);
        }

        return true;
    }

    private static Task claimTask(Connection connection, String workerId) throws SQLException {
        String sql =
                "WITH picked AS ( " +
                        "    SELECT task_id " +
                        "    FROM tasks " +
                        "    WHERE status = 'READY' " +
                        "      AND scheduled_at <= now() " +
                        "    ORDER BY priority DESC, scheduled_at ASC, created_at ASC " +
                        "    FOR UPDATE SKIP LOCKED " +
                        "    LIMIT 1 " +
                        ") " +
                        "UPDATE tasks t " +
                        "SET status = 'RUNNING', " +
                        "    started_at = COALESCE(started_at, now()), " +
                        "    locked_by = ?, " +
                        "    updated_at = now() " +
                        "FROM picked " +
                        "WHERE t.task_id = picked.task_id " +
                        "RETURNING t.task_id, t.task_type, t.priority, t.attempts, t.max_attempts";

        connection.setAutoCommit(false);

        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, workerId);

            try (ResultSet rs = statement.executeQuery()) {
                if (!rs.next()) {
                    connection.rollback();
                    return null;
                }

                Task task = new Task();
                task.taskId = rs.getLong("task_id");
                task.taskType = rs.getString("task_type");
                task.priority = rs.getInt("priority");
                task.attempts = rs.getInt("attempts");
                task.maxAttempts = rs.getInt("max_attempts");

                connection.commit();

                return task;
            }
        } catch (SQLException e) {
            connection.rollback();
            throw e;
        }
    }

    private static void completeTask(Connection connection, Task task, String workerId) throws SQLException {
        String sql =
                "UPDATE tasks " +
                        "SET status = 'COMPLETED', " +
                        "    completed_at = now(), " +
                        "    updated_at = now(), " +
                        "    locked_by = NULL " +
                        "WHERE task_id = ?";

        connection.setAutoCommit(false);

        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setLong(1, task.taskId);
            statement.executeUpdate();
            connection.commit();

            System.out.println(workerId + " completed task_id=" + task.taskId);
        } catch (SQLException e) {
            connection.rollback();
            throw e;
        }
    }

    private static void failTask(Connection connection, Task task, String workerId) throws SQLException {
        connection.setAutoCommit(false);

        if (task.attempts + 1 >= task.maxAttempts) {
            String sql =
                    "UPDATE tasks " +
                            "SET status = 'FAILED', " +
                            "    attempts = attempts + 1, " +
                            "    failed_at = now(), " +
                            "    updated_at = now(), " +
                            "    locked_by = NULL, " +
                            "    last_error = ? " +
                            "WHERE task_id = ?";

            try (PreparedStatement statement = connection.prepareStatement(sql)) {
                statement.setString(1, "Max attempts reached by " + workerId);
                statement.setLong(2, task.taskId);
                statement.executeUpdate();
                connection.commit();

                System.out.println(workerId + " moved task_id=" + task.taskId + " to FAILED");
            } catch (SQLException e) {
                connection.rollback();
                throw e;
            }
        } else {
            String sql =
                    "UPDATE tasks " +
                            "SET status = 'READY', " +
                            "    attempts = attempts + 1, " +
                            "    scheduled_at = now() + ((5 * POWER(2, attempts))::int * interval '1 minute'), " +
                            "    updated_at = now(), " +
                            "    locked_by = NULL, " +
                            "    last_error = ? " +
                            "WHERE task_id = ?";

            try (PreparedStatement statement = connection.prepareStatement(sql)) {
                statement.setString(1, "Temporary error in " + workerId);
                statement.setLong(2, task.taskId);
                statement.executeUpdate();
                connection.commit();

                System.out.println(workerId + " retry task_id=" + task.taskId);
            } catch (SQLException e) {
                connection.rollback();
                throw e;
            }
        }
    }

    private static void runMonitor() throws Exception {
        System.out.println("ts,ready,running,completed,failed,queue_lag_seconds,throughput_per_second,avg_wait_priority_100,avg_wait_priority_0");

        String sql =
                "SELECT " +
                        "    COUNT(*) FILTER (WHERE status = 'READY') AS ready, " +
                        "    COUNT(*) FILTER (WHERE status = 'RUNNING') AS running, " +
                        "    COUNT(*) FILTER (WHERE status = 'COMPLETED') AS completed, " +
                        "    COUNT(*) FILTER (WHERE status = 'FAILED') AS failed, " +
                        "    COALESCE(EXTRACT(EPOCH FROM (now() - MIN(created_at) FILTER (WHERE status = 'READY' AND scheduled_at <= now()))), 0) AS queue_lag_seconds, " +
                        "    COUNT(*) FILTER (WHERE status = 'COMPLETED' AND completed_at >= now() - interval '1 second') AS throughput_per_second, " +
                        "    COALESCE(AVG(EXTRACT(EPOCH FROM (started_at - created_at))) FILTER (WHERE priority = 100 AND started_at IS NOT NULL), 0) AS avg_wait_priority_100, " +
                        "    COALESCE(AVG(EXTRACT(EPOCH FROM (started_at - created_at))) FILTER (WHERE priority = 0 AND started_at IS NOT NULL), 0) AS avg_wait_priority_0 " +
                        "FROM tasks";

        try (
                Connection connection = connect();
                PreparedStatement statement = connection.prepareStatement(sql)
        ) {
            while (true) {
                try (ResultSet rs = statement.executeQuery()) {
                    rs.next();

                    System.out.printf(
                            "%s,%d,%d,%d,%d,%.3f,%d,%.3f,%.3f%n",
                            LocalDateTime.now(),
                            rs.getLong("ready"),
                            rs.getLong("running"),
                            rs.getLong("completed"),
                            rs.getLong("failed"),
                            rs.getDouble("queue_lag_seconds"),
                            rs.getLong("throughput_per_second"),
                            rs.getDouble("avg_wait_priority_100"),
                            rs.getDouble("avg_wait_priority_0")
                    );
                }

                Thread.sleep(1000);
            }
        }
    }

    private static class Task {
        long taskId;
        String taskType;
        int priority;
        int attempts;
        int maxAttempts;
    }
}