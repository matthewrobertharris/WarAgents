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

public class TestMoveUp extends TestCase {

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
	public void testMoveUp_Success_Flat() {
		String file = "resources\\test\\outputMaps\\test_moveUp_success_flat.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int x = agent.getX();
		int y = agent.getY();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_UP);
		assertTrue(map.getAllAgents().size() == 1);
		assertTrue(x == agent.getX());
		assertTrue((y + 1) == agent.getY());
	}	
	
	@Test
	public void testMoveUp_Success_FlatCarrying() {
		String file = "resources\\test\\outputMaps\\test_moveUp_success_flatCarrying.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		agent.setDirt(Agent.PICKUP_DIRT);
		int health = agent.getHealth();
		int x = agent.getX();
		int y = agent.getY();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_UP);
		assertTrue(map.getAllAgents().size() == 1);
		assertTrue(agent.getHealth() == (health - Agent.MOVE_HEALTH));
		assertTrue(x == agent.getX());
		assertTrue((y + 1) == agent.getY());
	}	
	
	@Test
	public void testMoveUp_Success_HeightDifference() {
		String file = "resources\\test\\outputMaps\\test_moveUp_success_heightDifference.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int health = agent.getHealth();
		int x = agent.getX();
		int y = agent.getY();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_UP);
		assertTrue(map.getAllAgents().size() == 1);
		assertTrue(agent.getHealth() == (health - Agent.MOVE_HEALTH));
		assertTrue(x == agent.getX());
		assertTrue((y + 1) == agent.getY());
	}	
	
	@Test
	public void testMoveUp_Success_HeightCarrying() {
		String file = "resources\\test\\outputMaps\\test_moveUp_success_heightCarrying.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		agent.setDirt(Agent.PICKUP_DIRT);
		int health = agent.getHealth();
		int x = agent.getX();
		int y = agent.getY();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_UP);
		assertTrue(map.getAllAgents().size() == 1);
		assertTrue(agent.getHealth() == (health - (2 * Agent.MOVE_HEALTH)));
		assertTrue(x == agent.getX());
		assertTrue((y + 1) == agent.getY());
	}	
	
	@Test
	public void testMoveUp_Fail_HeightDifference() {
		String file = "resources\\test\\outputMaps\\test_moveUp_fail_heightDifference.map";
		String error = "Cannot MOVE_UP because of height difference\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int health = agent.getHealth();
		int x = agent.getX();
		int y = agent.getY();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_UP);
		assertTrue(map.getAllAgents().size() == 1);
		assertTrue(agent.getHealth() == health);
		assertTrue(x == agent.getX());
		assertTrue(y == agent.getY());
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testMoveUp_Fail_HeightKill() {
		String file = "resources\\test\\outputMaps\\test_moveUp_fail_heightKill.map";
		String error = "Cannot MOVE_UP because move would kill\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		agent.setHealth(Agent.MOVE_HEALTH);
		int x = agent.getX();
		int y = agent.getY();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_UP);
		assertTrue(map.getAllAgents().size() == 1);
		assertTrue(agent.getHealth() == Agent.MOVE_HEALTH);
		assertTrue(x == agent.getX());
		assertTrue(y == agent.getY());
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testMoveUp_Fail_HeightCarryingKill() {
		String file = "resources\\test\\outputMaps\\test_moveUp_fail_heightCarryingKill.map";
		String error = "Cannot MOVE_UP because move would kill\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		agent.setDirt(Agent.PICKUP_DIRT);
		agent.setHealth(Agent.MOVE_HEALTH * 2);
		int x = agent.getX();
		int y = agent.getY();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_UP);
		assertTrue(map.getAllAgents().size() == 1);
		assertTrue(agent.getHealth() == (Agent.MOVE_HEALTH * 2));
		assertTrue(x == agent.getX());
		assertTrue(y == agent.getY());
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testMoveUp_Fail_CarryingKill() {
		String file = "resources\\test\\outputMaps\\test_moveUp_fail_carryingKill.map";
		String error = "Cannot MOVE_UP because move would kill\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		agent.setDirt(Agent.PICKUP_DIRT);
		agent.setHealth(Agent.MOVE_HEALTH);
		int x = agent.getX();
		int y = agent.getY();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_UP);
		assertTrue(map.getAllAgents().size() == 1);
		assertTrue(agent.getHealth() == Agent.MOVE_HEALTH);
		assertTrue(x == agent.getX());
		assertTrue(y == agent.getY());
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testMoveUp_Fail_Occupied() {
		String file = "resources\\test\\outputMaps\\test_moveUp_fail_occupied.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int x = agent.getX();
		int y = agent.getY();
		String secondAgent = map.getAllAgents().get(1).getID();
		String error = "Cannot MOVE_UP because of " + secondAgent + "\r\n";
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_UP);
		assertTrue(map.getAllAgents().size() == 2);
		assertTrue(x == agent.getX());
		assertTrue(y == agent.getY());
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testMoveUp_Fail_OutOfBounds() {
		String file = "resources\\test\\outputMaps\\test_moveUp_fail_outOfBounds.map";
		String error = "Cannot MOVE_UP because of out of bounds\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int x = agent.getX();
		int y = agent.getY();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_UP);
		assertTrue(x == agent.getX());
		assertTrue(y == agent.getY());
		assertEquals(outContent.toString(), error);
		
	}
}
