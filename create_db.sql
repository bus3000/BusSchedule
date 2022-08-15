ALTER USER postgres WITH PASSWORD 'temp123!';

DROP TABLE IF EXISTS public.schedule;
DROP TABLE IF EXISTS public.bus;
DROP TABLE IF EXISTS public.driver;
DROP TABLE IF EXISTS public.bus_user;

--Table: public.driver
CREATE TABLE public.driver
(
    id serial PRIMARY KEY,
	first_name VARCHAR(64),
	last_name VARCHAR(64),
	ssn int,
	email varchar(64)
);
ALTER TABLE IF EXISTS public.driver
    OWNER to postgres;

-- Table: public.bus

CREATE TABLE public.bus
(
    id serial PRIMARY KEY,
	capacity int,
	model VARCHAR(64),
	make VARCHAR(64)
);
ALTER TABLE IF EXISTS public.bus
    OWNER to postgres;
	
	
-- Table: public.schedule

CREATE TABLE public.schedule
(
	id serial PRIMARY KEY,
    bus_id int,
	driver_id int,
	start_datetime BIGINT,
	end_datetime BIGINT,
	CONSTRAINT fk_bus
		FOREIGN KEY(bus_id) 
			REFERENCES bus(id),
	CONSTRAINT fk_driver
		FOREIGN KEY(driver_id) 
			REFERENCES driver(id)
);
ALTER TABLE IF EXISTS public.schedule
    OWNER to postgres;
	
CREATE TABLE public.bus_user
(
	id serial PRIMARY KEY,
	email VARCHAR(64),
	password VARCHAR(64),
	joined_on BIGINT,
	admin BOOLEAN
);

ALTER TABLE IF EXISTS public.bus_user
    OWNER to postgres;

INSERT INTO driver (first_name, last_name, email, ssn)
VALUES ('John', 'Doe', 'jd@busbus.ca', 123456789),
	('Jane', 'Smith', 'sj@busbus.ca', 987654321);

INSERT INTO bus (capacity, model, make)
VALUES (64, 'MODELX', 'MAKEX'),
	 (120, 'MODELY', 'MAKEY');

INSERT INTO schedule (bus_id, driver_id, start_datetime, end_datetime)
VALUES (1,1,1660357004, 1660385804),
		(1,2,1660816800, 1660845600),
		(2,1,1660888800, 1660917600),
		(2,2,1661436000, 1661464800);
		
INSERT INTO bus_user (email, password, joined_on, admin)
VALUES 
('member@busbus.ca', 'securepass', 1660424991, false),
('admin@busbus.ca', 'SuP3Rs3cUr3P455!!', 1660424991, true);


select * from driver;
select * from bus;
select * from schedule;
select * from bus_user;