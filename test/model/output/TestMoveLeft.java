package model.output;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

import org.junit.After;
import org.junit.Test;

import junit.framework.TestCase;
import main.Game;
import model.Agent;
import model.Map;
import model.output.Action.Activity;
import readers.ActionReaderImpl;
import readers.CriteriaReaderImpl;
import readers.GameReader;
import readers.GameReaderImpl;
import readers.InputReaderImpl;
import readers.MapReaderImpl;
import readers.ModeReaderImpl;
import readers.PlantReaderImpl;
import readers.PlayerReaderImpl;
import readers.PositionReaderImpl;
import readers.TreeReaderImpl;

public class TestMoveLeft extends TestCase {

	private GameReader gameReader;
	private final ByteArrayOutputStream outContent = new ByteArrayOutputStream();

	@Override
	protected void setUp() {
		gameReader = new GameReaderImpl(new MapReaderImpl(new PlantReaderImpl(),
				new PlayerReaderImpl(new TreeReaderImpl(new ActionReaderImpl(new PositionReaderImpl()), new InputReaderImpl(new PositionReaderImpl()))),
				new CriteriaReaderImpl(new ActionReaderImpl(new PositionReaderImpl())), new ModeReaderImpl()));
		System.setOut(new PrintStream(outContent));
	}
	
	@After
	public void cleanUpStreams() {
	    System.setOut(null);
	}

	@Test
	public void testMoveLeft_Success_Flat() {
		String file = "resources\\test\\outputMaps\\test_moveLeft_success_flat.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int x = agent.getX();
		int y = agent.getY();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_LEFT);
		assertTrue(map.getAllAgents().size() == 1);
		assertTrue((x - 1) == agent.getX());
		assertTrue(y == agent.getY());
	}	
	
	@Test
	public void testMoveLeft_Success_FlatCarryingDirt() {
		String file = "resources\\test\\outputMaps\\test_moveLeft_success_flatCarryingDirt.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		agent.setDirt(Agent.PICKUP_DIRT);
		int health = agent.getHealth();
		int x = agent.getX();
		int y = agent.getY();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_LEFT);
		assertTrue(map.getAllAgents().size() == 1);
		assertTrue(agent.getHealth() == (health - Agent.MOVE_HEALTH));
		assertTrue((x - 1) == agent.getX());
		assertTrue(y == agent.getY());
	}	
	
	@Test
	public void testMoveLeft_Success_FlatCarryingFood() {
		String file = "resources\\test\\outputMaps\\test_moveLeft_success_flatCarryingFood.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		agent.setFood(Agent.PICKUP_FOOD);
		int health = agent.getHealth();
		int x = agent.getX();
		int y = agent.getY();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_LEFT);
		assertTrue(map.getAllAgents().size() == 1);
		assertTrue(agent.getHealth() == (health - Agent.MOVE_HEALTH));
		assertTrue((x - 1) == agent.getX());
		assertTrue(y == agent.getY());
	}	
	
	@Test
	public void testMoveLeft_Success_HeightDifference() {
		String file = "resources\\test\\outputMaps\\test_moveLeft_success_heightDifference.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int health = agent.getHealth();
		int x = agent.getX();
		int y = agent.getY();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_LEFT);
		assertTrue(map.getAllAgents().size() == 1);
		assertTrue(agent.getHealth() == (health - Agent.MOVE_HEALTH));
		assertTrue((x - 1) == agent.getX());
		assertTrue(y == agent.getY());
	}	
	
	@Test
	public void testMoveLeft_Success_HeightCarryingDirt() {
		String file = "resources\\test\\outputMaps\\test_moveLeft_success_heightCarryingDirt.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		agent.setDirt(Agent.PICKUP_DIRT);
		int health = agent.getHealth();
		int x = agent.getX();
		int y = agent.getY();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_LEFT);
		assertTrue(map.getAllAgents().size() == 1);
		assertTrue(agent.getHealth() == (health - (2 * Agent.MOVE_HEALTH)));
		assertTrue((x - 1) == agent.getX());
		assertTrue(y == agent.getY());
	}	
	
	@Test
	public void testMoveLeft_Success_HeightCarryingFood() {
		String file = "resources\\test\\outputMaps\\test_moveLeft_success_heightCarryingFood.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		agent.setFood(Agent.PICKUP_FOOD);
		int health = agent.getHealth();
		int x = agent.getX();
		int y = agent.getY();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_LEFT);
		assertTrue(map.getAllAgents().size() == 1);
		assertTrue(agent.getHealth() == (health - (2 * Agent.MOVE_HEALTH)));
		assertTrue((x - 1) == agent.getX());
		assertTrue(y == agent.getY());
	}
	
	@Test
	public void testMoveLeft_Fail_HeightDifference() {
		String file = "resources\\test\\outputMaps\\test_moveLeft_fail_heightDifference.map";
		String error = "Cannot MOVE_LEFT because of height difference\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int health = agent.getHealth();
		int x = agent.getX();
		int y = agent.getY();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_LEFT);
		assertTrue(map.getAllAgents().size() == 1);
		assertTrue(agent.getHealth() == health);
		assertTrue(x == agent.getX());
		assertTrue(y == agent.getY());
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testMoveLeft_Fail_HeightKill() {
		String file = "resources\\test\\outputMaps\\test_moveLeft_fail_heightKill.map";
		String error = "Cannot MOVE_LEFT because move would kill\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		agent.setHealth(Agent.MOVE_HEALTH);
		int x = agent.getX();
		int y = agent.getY();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_LEFT);
		assertTrue(map.getAllAgents().size() == 1);
		assertTrue(agent.getHealth() == Agent.MOVE_HEALTH);
		assertTrue(x == agent.getX());
		assertTrue(y == agent.getY());
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testMoveLeft_Fail_HeightCarryingKill() {
		String file = "resources\\test\\outputMaps\\test_moveLeft_fail_heightCarryingKill.map";
		String error = "Cannot MOVE_LEFT because move would kill\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		agent.setDirt(Agent.PICKUP_DIRT);
		agent.setHealth(Agent.MOVE_HEALTH * 2);
		int x = agent.getX();
		int y = agent.getY();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_LEFT);
		assertTrue(map.getAllAgents().size() == 1);
		assertTrue(agent.getHealth() == (Agent.MOVE_HEALTH * 2));
		assertTrue(x == agent.getX());
		assertTrue(y == agent.getY());
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testMoveLeft_Fail_CarryingKill() {
		String file = "resources\\test\\outputMaps\\test_moveLeft_fail_carryingKill.map";
		String error = "Cannot MOVE_LEFT because move would kill\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		agent.setDirt(Agent.PICKUP_DIRT);
		agent.setHealth(Agent.MOVE_HEALTH);
		int x = agent.getX();
		int y = agent.getY();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_LEFT);
		assertTrue(map.getAllAgents().size() == 1);
		assertTrue(agent.getHealth() == Agent.MOVE_HEALTH);
		assertTrue(x == agent.getX());
		assertTrue(y == agent.getY());
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testMoveLeft_Fail_Occupied() {
		String file = "resources\\test\\outputMaps\\test_moveLeft_fail_occupied.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int x = agent.getX();
		int y = agent.getY();
		String secondAgent = map.getAllAgents().get(1).getID();
		String error = "Cannot MOVE_LEFT because of " + secondAgent + "\r\n";
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_LEFT);
		assertTrue(map.getAllAgents().size() == 2);
		assertTrue(x == agent.getX());
		assertTrue(y == agent.getY());
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testMoveLeft_Fail_OutOfBounds() {
		String file = "resources\\test\\outputMaps\\test_moveLeft_fail_outOfBounds.map";
		String error = "Cannot MOVE_LEFT because of out of bounds\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int x = agent.getX();
		int y = agent.getY();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_LEFT);
		assertTrue(x == agent.getX());
		assertTrue(y == agent.getY());
		assertEquals(outContent.toString(), error);
		
	}
	
	@Test
	public void test_ToString() {
		MoveLeft output = new MoveLeft();
		String strOutput = "MOVE_LEFT";
		assertTrue(output.toString().equals(strOutput));
	}
}
